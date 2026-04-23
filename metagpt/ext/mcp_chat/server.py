#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""aiohttp server for hardened multi-model MCP chat."""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml
from aiohttp import web
from pydantic import BaseModel, Field, ValidationError

from metagpt.const import METAGPT_ROOT
from metagpt.ext.mcp_chat.service import (
    DEFAULT_SYSTEM_PROMPT,
    MCPChatService,
    ModelClient,
    MultiModelChatEngine,
    SessionStore,
    WebhookDispatcher,
    compose_system_prompt,
    load_declared_skill_names,
    load_resource_packs,
    verify_payload_signature,
)


def _ensure_provider_registered(api_type: str) -> None:
    """Import provider module on demand so optional deps stay optional."""
    provider_imports = {
        "openai": "metagpt.provider.openai_api",
        "fireworks": "metagpt.provider.openai_api",
        "open_llm": "metagpt.provider.openai_api",
        "moonshot": "metagpt.provider.openai_api",
        "mistral": "metagpt.provider.openai_api",
        "yi": "metagpt.provider.openai_api",
        "open_router": "metagpt.provider.openai_api",
        "deepseek": "metagpt.provider.openai_api",
        "siliconflow": "metagpt.provider.openai_api",
        "openrouter": "metagpt.provider.openai_api",
        "llama_api": "metagpt.provider.openai_api",
        "anthropic": "metagpt.provider.anthropic_api",
        "claude": "metagpt.provider.anthropic_api",
        "gemini": "metagpt.provider.google_gemini_api",
        "ollama": "metagpt.provider.ollama_api",
        "ollama.generate": "metagpt.provider.ollama_api",
        "ollama.embed": "metagpt.provider.ollama_api",
        "ollama.embeddings": "metagpt.provider.ollama_api",
        "azure": "metagpt.provider.azure_openai_api",
        "zhipuai": "metagpt.provider.zhipuai_api",
        "spark": "metagpt.provider.spark_api",
        "qianfan": "metagpt.provider.qianfan_api",
        "dashscope": "metagpt.provider.dashscope_api",
        "bedrock": "metagpt.provider.bedrock_api",
        "ark": "metagpt.provider.ark_api",
        "openrouter_reasoning": "metagpt.provider.openrouter_reasoning",
        "metagpt": "metagpt.provider.metagpt_api",
    }
    module_name = provider_imports.get(api_type)
    if module_name:
        __import__(module_name)


def _is_provider_registered(api_type: Any) -> bool:
    try:
        from metagpt.provider.llm_provider_registry import LLM_REGISTRY
    except Exception:
        return False
    return api_type in LLM_REGISTRY.providers


class MCPChatSettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 18789
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    resource_pack_dir: str = "docs/resources/mcp_chat_packs"
    max_message_chars: int = 8000
    timeout_seconds: int = 120

    inbound_signature_secret: str = ""
    webhook_url: str = ""
    webhook_secret: str = ""

    models: List[Dict[str, Any]] = Field(default_factory=list)

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "MCPChatSettings":
        """Load settings from YAML and environment variables."""
        path = config_path or Path(
            os.getenv("MCP_CHAT_CONFIG_PATH", str(METAGPT_ROOT / "config/mcp_chat.yaml"))
        )
        file_data: Dict[str, Any] = {}
        if path.exists():
            loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if isinstance(loaded, dict):
                file_data = loaded

        env_data: Dict[str, Any] = {}
        mapping = {
            "MCP_CHAT_HOST": "host",
            "MCP_CHAT_PORT": "port",
            "MCP_CHAT_SYSTEM_PROMPT": "system_prompt",
            "MCP_CHAT_RESOURCE_PACK_DIR": "resource_pack_dir",
            "MCP_CHAT_MAX_MESSAGE_CHARS": "max_message_chars",
            "MCP_CHAT_TIMEOUT_SECONDS": "timeout_seconds",
            "MCP_CHAT_INBOUND_SIGNATURE_SECRET": "inbound_signature_secret",
            "MCP_CHAT_WEBHOOK_URL": "webhook_url",
            "MCP_CHAT_WEBHOOK_SECRET": "webhook_secret",
        }
        for env_key, target_key in mapping.items():
            value = os.getenv(env_key)
            if value not in (None, ""):
                env_data[target_key] = value

        models_json = os.getenv("MCP_CHAT_MODELS_JSON", "")
        if models_json:
            env_data["models"] = json.loads(models_json)
        elif "models" not in file_data:
            env_data["models"] = cls._models_from_split_env()

        merged = {**file_data, **env_data}
        return cls.model_validate(merged)

    @staticmethod
    def _models_from_split_env() -> List[Dict[str, Any]]:
        primary = {
            "name": os.getenv("MCP_CHAT_PRIMARY_NAME", "local-ollama"),
            "api_type": os.getenv("MCP_CHAT_PRIMARY_API_TYPE", "ollama"),
            "base_url": os.getenv("MCP_CHAT_PRIMARY_BASE_URL", "http://127.0.0.1:11434/api"),
            "api_key": os.getenv("MCP_CHAT_PRIMARY_API_KEY", "ollama"),
            "model": os.getenv("MCP_CHAT_PRIMARY_MODEL", "llama3.1:8b"),
        }
        fallback_model = os.getenv("MCP_CHAT_FALLBACK_MODEL")
        if not fallback_model:
            return [primary]

        fallback = {
            "name": os.getenv("MCP_CHAT_FALLBACK_NAME", "fallback"),
            "api_type": os.getenv("MCP_CHAT_FALLBACK_API_TYPE", "openai"),
            "base_url": os.getenv("MCP_CHAT_FALLBACK_BASE_URL", "https://api.openai.com/v1"),
            "api_key": os.getenv("MCP_CHAT_FALLBACK_API_KEY", ""),
            "model": fallback_model,
        }
        return [primary, fallback]


def _resolve_path(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else (METAGPT_ROOT / path).resolve()


def _build_model_clients(
    settings: MCPChatSettings,
    llm_factory: Optional[Callable[[Any], Any]] = None,
) -> List[ModelClient]:
    from metagpt.configs.llm_config import LLMConfig, LLMType

    if not settings.models:
        raise ValueError("No models configured; set MCP_CHAT_MODELS_JSON or config/mcp_chat.yaml")

    clients: List[ModelClient] = []
    for idx, model_obj in enumerate(settings.models):
        if not isinstance(model_obj, dict):
            raise ValueError(f"Model config at index {idx} is not an object")
        model_input = dict(model_obj)
        api_type = model_input.get("api_type")
        if isinstance(api_type, str):
            model_input["api_type"] = LLMType(api_type)
        config = LLMConfig.model_validate(model_input)
        if llm_factory is not None:
            create_llm = llm_factory
        else:
            if not _is_provider_registered(config.api_type):
                _ensure_provider_registered(config.api_type)
            from metagpt.provider.llm_provider_registry import create_llm_instance

            create_llm = create_llm_instance
        llm = create_llm(config)
        label = model_obj.get("name") or config.model or f"model-{idx}"
        clients.append(ModelClient(label=label, llm=llm))
    return clients


def build_service(
    settings: MCPChatSettings,
    skip_skill_discovery: bool = False,
) -> MCPChatService:
    model_clients = _build_model_clients(settings)
    engine = MultiModelChatEngine(clients=model_clients, timeout_seconds=settings.timeout_seconds)
    packs = load_resource_packs(_resolve_path(settings.resource_pack_dir))
    system_prompt = compose_system_prompt(settings.system_prompt, packs)
    declared_skills = [] if skip_skill_discovery else load_declared_skill_names()

    return MCPChatService(
        engine=engine,
        session_store=SessionStore(),
        webhook_dispatcher=WebhookDispatcher(settings.webhook_url, settings.webhook_secret),
        system_prompt=system_prompt,
        declared_skill_names=declared_skills,
        max_message_chars=settings.max_message_chars,
    )


def _json_error(message: str, status: int = 400) -> web.Response:
    return web.json_response({"error": message}, status=status)


async def health(request: web.Request) -> web.Response:
    service: MCPChatService = request.app["chat_service"]
    return web.json_response(
        {
            "status": "ok",
            "models": service.engine.list_models(),
            "skills": sorted(service.declared_skill_names),
        }
    )


async def chat_get(request: web.Request) -> web.Response:
    service: MCPChatService = request.app["chat_service"]
    session_id = request.query.get("session", "main")
    snapshot = await service.session_snapshot(session_id)
    return web.json_response(snapshot)


async def chat_post(request: web.Request) -> web.Response:
    service: MCPChatService = request.app["chat_service"]
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return _json_error("Invalid JSON body")
    if not isinstance(body, dict):
        return _json_error("Body must be a JSON object")

    session_id = str(body.get("session", "main"))
    message = body.get("message")
    if not isinstance(message, str):
        return _json_error("`message` must be a string")
    preferred_models = body.get("preferred_models")
    if preferred_models is not None and not isinstance(preferred_models, list):
        return _json_error("`preferred_models` must be a string array when provided")

    try:
        result = await service.chat(
            session_id=session_id,
            message=message,
            preferred_models=preferred_models,
            metadata={"endpoint": "/chat", "client_ip": request.remote},
        )
    except ValueError as exc:
        return _json_error(str(exc), status=400)
    except RuntimeError as exc:
        return _json_error(str(exc), status=503)
    return web.json_response(result)


async def chat_completions(request: web.Request) -> web.Response:
    service: MCPChatService = request.app["chat_service"]
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return _json_error("Invalid JSON body")
    if not isinstance(body, dict):
        return _json_error("Body must be a JSON object")

    messages = body.get("messages", [])
    if not isinstance(messages, list) or not messages:
        return _json_error("`messages` must be a non-empty array")

    user_message: Optional[str] = None
    for item in reversed(messages):
        if isinstance(item, dict) and item.get("role") == "user" and isinstance(item.get("content"), str):
            user_message = item["content"]
            break
    if not user_message:
        return _json_error("No user message found in `messages`")

    model = body.get("model")
    preferred_models: Optional[List[str]] = None
    if isinstance(model, str) and model:
        preferred_models = [model]
    if isinstance(body.get("preferred_models"), list):
        preferred_models = body["preferred_models"]

    session_id = str(body.get("session", "main"))
    stream = bool(body.get("stream"))

    if stream:
        stream_response = web.StreamResponse(
            status=200,
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
        await stream_response.prepare(request)

        now_ts = int(time.time())
        completion_id = f"chatcmpl-{now_ts}-{uuid.uuid4().hex[:8]}"

        try:
            async for chunk, source, is_final in service.stream_chat_completion_chunks(
                session_id=session_id,
                message=user_message,
                preferred_models=preferred_models,
                metadata={"endpoint": "/v1/chat/completions", "client_ip": request.remote, "stream": True},
            ):
                if is_final:
                    payload = {
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": now_ts,
                        "model": source,
                        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                    }
                else:
                    payload = {
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": now_ts,
                        "model": source,
                        "choices": [{"index": 0, "delta": {"content": chunk}, "finish_reason": None}],
                    }
                await stream_response.write(f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8"))
            await stream_response.write(b"data: [DONE]\n\n")
        except ValueError as exc:
            err = {"error": {"message": str(exc), "type": "invalid_request_error"}}
            await stream_response.write(f"data: {json.dumps(err, ensure_ascii=False)}\n\n".encode("utf-8"))
            await stream_response.write(b"data: [DONE]\n\n")
        except RuntimeError as exc:
            err = {"error": {"message": str(exc), "type": "service_unavailable"}}
            await stream_response.write(f"data: {json.dumps(err, ensure_ascii=False)}\n\n".encode("utf-8"))
            await stream_response.write(b"data: [DONE]\n\n")
        finally:
            await stream_response.write_eof()

        return stream_response

    try:
        result = await service.chat(
            session_id=session_id,
            message=user_message,
            preferred_models=preferred_models,
            metadata={"endpoint": "/v1/chat/completions", "client_ip": request.remote},
        )
    except ValueError as exc:
        return _json_error(str(exc), status=400)
    except RuntimeError as exc:
        return _json_error(str(exc), status=503)

    now_ts = int(time.time())
    response = {
        "id": f"chatcmpl-{now_ts}",
        "object": "chat.completion",
        "created": now_ts,
        "model": result["source"],
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": result["response"]},
                "finish_reason": "stop",
            }
        ],
    }
    return web.json_response(response)


async def mcp_events(request: web.Request) -> web.Response:
    settings: MCPChatSettings = request.app["settings"]
    body_raw = await request.text()
    if settings.inbound_signature_secret:
        ts = request.headers.get("X-MetaGPT-Timestamp", "")
        sig = request.headers.get("X-MetaGPT-Signature", "")
        if not verify_payload_signature(
            settings.inbound_signature_secret,
            timestamp=ts,
            body=body_raw,
            signature=sig,
        ):
            return _json_error("Invalid webhook signature", status=401)

    try:
        payload = json.loads(body_raw or "{}")
    except json.JSONDecodeError:
        return _json_error("Invalid JSON body")
    if not isinstance(payload, dict):
        return _json_error("Body must be a JSON object")

    session_id = str(payload.get("session", "main"))
    event = payload.get("event")
    event_payload = payload.get("payload", {})
    if not isinstance(event, str) or not event:
        return _json_error("`event` must be a non-empty string")
    if not isinstance(event_payload, dict):
        return _json_error("`payload` must be an object")

    service: MCPChatService = request.app["chat_service"]
    result = await service.ingest_mcp_event(session_id=session_id, event=event, payload=event_payload)
    return web.json_response(result, status=202)


def _mcp_response(req_id: Any, result: Any) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _mcp_error(req_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


async def _handle_mcp_rpc_single(service: MCPChatService, request_obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    req_id = request_obj.get("id")
    method = request_obj.get("method")
    params = request_obj.get("params", {})

    if request_obj.get("jsonrpc") != "2.0":
        return _mcp_error(req_id, -32600, "Invalid Request: jsonrpc must be '2.0'")
    if not isinstance(method, str) or not method:
        return _mcp_error(req_id, -32600, "Invalid Request: method must be non-empty string")
    if params is None:
        params = {}
    if not isinstance(params, dict):
        return _mcp_error(req_id, -32602, "Invalid params: expected object")

    # Notifications do not include an id and should not produce a response.
    is_notification = req_id is None

    try:
        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "metagpt-mcp-chat", "version": "0.1.0"},
                "capabilities": {"tools": {"listChanged": False}},
            }
            return None if is_notification else _mcp_response(req_id, result)

        if method in {"ping"}:
            return None if is_notification else _mcp_response(req_id, {})

        if method in {"tools/list", "tools.list"}:
            result = {"tools": service.list_mcp_tools()}
            return None if is_notification else _mcp_response(req_id, result)

        if method in {"tools/call", "tools.call"}:
            name = params.get("name")
            arguments = params.get("arguments", {})
            if not isinstance(name, str) or not name:
                return _mcp_error(req_id, -32602, "Invalid params: `name` must be non-empty string")
            if not isinstance(arguments, dict):
                return _mcp_error(req_id, -32602, "Invalid params: `arguments` must be object")
            tool_result = await service.call_mcp_tool(name=name, arguments=arguments)
            result = {"content": [{"type": "text", "text": json.dumps(tool_result, ensure_ascii=False)}], "isError": False}
            return None if is_notification else _mcp_response(req_id, result)

        if method in {"events/subscribe", "events.subscribe"}:
            session_id = params.get("session")
            if session_id is not None and not isinstance(session_id, str):
                return _mcp_error(req_id, -32602, "Invalid params: `session` must be string")
            query = f"?session={session_id}" if session_id else ""
            result = {"streamUrl": f"/v1/mcp/events/stream{query}"}
            return None if is_notification else _mcp_response(req_id, result)

        return _mcp_error(req_id, -32601, f"Method not found: {method}")
    except ValueError as exc:
        return _mcp_error(req_id, -32602, str(exc))
    except Exception as exc:
        return _mcp_error(req_id, -32000, f"Server error: {exc}")


async def mcp_rpc(request: web.Request) -> web.Response:
    service: MCPChatService = request.app["chat_service"]
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return web.json_response(_mcp_error(None, -32700, "Parse error"), status=400)

    if isinstance(payload, list):
        responses: List[Dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, dict):
                responses.append(_mcp_error(None, -32600, "Invalid Request"))
                continue
            resp = await _handle_mcp_rpc_single(service, item)
            if resp is not None:
                responses.append(resp)
        if not responses:
            return web.Response(status=204)
        return web.json_response(responses)

    if not isinstance(payload, dict):
        return web.json_response(_mcp_error(None, -32600, "Invalid Request"), status=400)

    resp = await _handle_mcp_rpc_single(service, payload)
    if resp is None:
        return web.Response(status=204)
    return web.json_response(resp)


async def mcp_events_stream(request: web.Request) -> web.StreamResponse:
    service: MCPChatService = request.app["chat_service"]
    session_filter = request.query.get("session")
    if session_filter == "":
        session_filter = None
    max_events_raw = request.query.get("max_events")
    max_events: Optional[int] = None
    if max_events_raw:
        try:
            parsed = int(max_events_raw)
            if parsed > 0:
                max_events = parsed
        except ValueError:
            max_events = None

    subscription_id, queue = await service.open_event_subscription(session_id=session_filter)
    response = web.StreamResponse(
        status=200,
        headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
    await response.prepare(request)
    emitted = 0
    try:
        ready_payload = {"type": "mcp.stream.ready", "session": session_filter}
        await response.write(f"data: {json.dumps(ready_payload, ensure_ascii=False)}\n\n".encode("utf-8"))
        emitted += 1
        if max_events is not None and emitted >= max_events:
            return response
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=25.0)
                await response.write(f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode("utf-8"))
                emitted += 1
                if max_events is not None and emitted >= max_events:
                    break
            except asyncio.TimeoutError:
                await response.write(b": keepalive\n\n")
    except (asyncio.CancelledError, ConnectionResetError):
        pass
    finally:
        await service.close_event_subscription(subscription_id)
        with contextlib.suppress(ConnectionResetError):
            await response.write_eof()
    return response


async def mcp_stdio(request: web.Request) -> web.Response:
    """Line-delimited JSON-RPC over HTTP for stdio-style MCP clients."""
    service: MCPChatService = request.app["chat_service"]
    raw = await request.text()
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if not lines:
        return web.Response(text="", content_type="application/x-ndjson")

    responses: List[Dict[str, Any]] = []
    for line in lines:
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            responses.append(_mcp_error(None, -32700, "Parse error"))
            continue
        if not isinstance(obj, dict):
            responses.append(_mcp_error(None, -32600, "Invalid Request"))
            continue
        resp = await _handle_mcp_rpc_single(service, obj)
        if resp is not None:
            responses.append(resp)

    if not responses:
        return web.Response(text="", content_type="application/x-ndjson")

    payload = "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in responses)
    return web.Response(text=payload, content_type="application/x-ndjson")


def create_app(
    settings: Optional[MCPChatSettings] = None,
    service_override: Optional[MCPChatService] = None,
    skip_skill_discovery: bool = False,
) -> web.Application:
    resolved_settings = settings or MCPChatSettings.load()
    service = service_override or build_service(resolved_settings, skip_skill_discovery=skip_skill_discovery)

    app = web.Application()
    app["settings"] = resolved_settings
    app["chat_service"] = service
    app.add_routes(
        [
            web.get("/health", health),
            web.get("/chat", chat_get),
            web.post("/chat", chat_post),
            web.post("/v1/chat/completions", chat_completions),
            web.post("/v1/mcp/events", mcp_events),
            web.post("/v1/mcp/rpc", mcp_rpc),
            web.post("/v1/mcp/stdio", mcp_stdio),
            web.get("/v1/mcp/events/stream", mcp_events_stream),
        ]
    )
    return app


def run_server(settings: Optional[MCPChatSettings] = None) -> None:
    """Entrypoint used by scripts and module execution."""
    try:
        resolved_settings = settings or MCPChatSettings.load()
    except ValidationError as exc:
        raise RuntimeError(f"Invalid MCP chat configuration: {exc}") from exc
    app = create_app(resolved_settings)
    web.run_app(app, host=resolved_settings.host, port=resolved_settings.port)


if __name__ == "__main__":
    run_server()
