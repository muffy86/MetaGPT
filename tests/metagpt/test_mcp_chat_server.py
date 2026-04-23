#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""HTTP-level tests for MCP chat aiohttp server."""

from __future__ import annotations

import json
import time

import pytest
from aiohttp.test_utils import TestClient, TestServer

from metagpt.ext.mcp_chat.server import MCPChatSettings, create_app
from metagpt.ext.mcp_chat.service import sign_payload


class _StubService:
    def __init__(self):
        self.declared_skill_names = {"web_search"}
        self.engine = type("Engine", (), {"list_models": lambda self: ["stub"]})()
        self._sessions = {}
        self._subscriber_queues = []

    async def chat(self, session_id: str, message: str, preferred_models=None, metadata=None):
        history = self._sessions.setdefault(session_id, [])
        reply = f"echo:{message}"
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": reply})
        await self._publish_event(
            {"type": "chat.completed", "session": session_id, "source": "stub", "message": message, "response": reply}
        )
        return {"session": session_id, "source": "stub", "message": message, "response": reply}

    async def session_snapshot(self, session_id: str):
        return {"session": session_id, "history": self._sessions.get(session_id, [])}

    async def ingest_mcp_event(self, session_id: str, event: str, payload: dict):
        await self._publish_event({"type": "mcp.event.ingested", "session": session_id, "event": event, "payload": payload})
        return {"status": "accepted", "session": session_id, "event": event, "payload": payload}

    async def _publish_event(self, event: dict):
        for queue, session_filter in list(self._subscriber_queues):
            if session_filter and session_filter != event.get("session"):
                continue
            queue.put_nowait(event)

    async def stream_chat_completion_chunks(
        self,
        session_id: str,
        message: str,
        preferred_models=None,
        metadata=None,
        chunk_size: int = 64,
    ):
        result = await self.chat(session_id=session_id, message=message, preferred_models=preferred_models, metadata=metadata)
        text = result["response"]
        source = result["source"]
        size = max(1, chunk_size)
        for ix in range(0, len(text), size):
            yield text[ix : ix + size], source, False
        yield "", source, True

    async def open_event_subscription(self, session_id=None):
        import asyncio

        queue = asyncio.Queue()
        self._subscriber_queues.append((queue, session_id))
        return 1, queue

    async def close_event_subscription(self, subscription_id: int):
        if self._subscriber_queues:
            self._subscriber_queues.pop(0)
        return None

    def list_mcp_tools(self):
        return [{"name": "chat.send"}, {"name": "chat.snapshot"}, {"name": "mcp.event.ingest"}]

    async def call_mcp_tool(self, name: str, arguments=None):
        args = arguments or {}
        if name == "chat.send":
            return await self.chat(session_id=str(args.get("session", "main")), message=str(args.get("message", "")))
        if name == "chat.snapshot":
            return await self.session_snapshot(str(args.get("session", "main")))
        if name == "mcp.event.ingest":
            return await self.ingest_mcp_event(
                session_id=str(args.get("session", "main")),
                event=str(args.get("event", "")),
                payload=args.get("payload", {}),
            )
        raise ValueError(f"unknown tool: {name}")


def _build_stub_app(settings: MCPChatSettings):
    app = create_app(
        settings=settings,
        service_override=_StubService(),
        skip_skill_discovery=True,
    )
    return app


@pytest.mark.asyncio
async def test_chat_get_post_and_openai_compat():
    settings = MCPChatSettings(
        models=[
            {
                "name": "dummy",
                "api_type": "ollama",
                "base_url": "http://127.0.0.1:11434/api",
                "api_key": "ollama",
                "model": "llama3.1:8b",
            }
        ]
    )
    app = _build_stub_app(settings)

    server = TestServer(app)
    async with server:
        client = TestClient(server)
        async with client:
            health_rsp = await client.get("/health")
            health_body = await health_rsp.json()
            assert health_rsp.status == 200
            assert health_body["status"] == "ok"

            post_rsp = await client.post("/chat", json={"session": "main", "message": "hello"})
            post_body = await post_rsp.json()
            assert post_rsp.status == 200
            assert post_body["response"] == "echo:hello"

            get_rsp = await client.get("/chat?session=main")
            get_body = await get_rsp.json()
            assert get_rsp.status == 200
            assert get_body["session"] == "main"
            assert len(get_body["history"]) == 2

            completion_rsp = await client.post(
                "/v1/chat/completions",
                json={
                    "session": "main",
                    "model": "stub",
                    "messages": [{"role": "user", "content": "test-completion"}],
                },
            )
            completion_body = await completion_rsp.json()
            assert completion_rsp.status == 200
            assert completion_body["choices"][0]["message"]["content"] == "echo:test-completion"

            stream_rsp = await client.post(
                "/v1/chat/completions",
                json={
                    "session": "main",
                    "stream": True,
                    "messages": [{"role": "user", "content": "test-stream"}],
                },
            )
            assert stream_rsp.status == 200
            stream_text = await stream_rsp.text()
            assert "chat.completion.chunk" in stream_text
            assert "data: [DONE]" in stream_text


@pytest.mark.asyncio
async def test_mcp_events_signature_required():
    settings = MCPChatSettings(
        inbound_signature_secret="super-secret",
        models=[
            {
                "name": "dummy",
                "api_type": "ollama",
                "base_url": "http://127.0.0.1:11434/api",
                "api_key": "ollama",
                "model": "llama3.1:8b",
            }
        ],
    )
    app = _build_stub_app(settings)

    payload = {"session": "main", "event": "tool.result", "payload": {"ok": True}}
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    timestamp = str(int(time.time()))
    signature = sign_payload(settings.inbound_signature_secret, timestamp, body)

    server = TestServer(app)
    async with server:
        client = TestClient(server)
        async with client:
            bad_rsp = await client.post("/v1/mcp/events", data=body, headers={"Content-Type": "application/json"})
            assert bad_rsp.status == 401

            ok_rsp = await client.post(
                "/v1/mcp/events",
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "X-MetaGPT-Timestamp": timestamp,
                    "X-MetaGPT-Signature": signature,
                },
            )
            ok_body = await ok_rsp.json()
            assert ok_rsp.status == 202
            assert ok_body["status"] == "accepted"


def test_build_model_clients_uses_registered_stub_provider():
    from metagpt.ext.mcp_chat import server as chat_server

    settings = MCPChatSettings(
        models=[
            {
                "name": "dummy",
                "api_type": "ollama",
                "base_url": "http://127.0.0.1:11434/api",
                "api_key": "ollama",
                "model": "llama3.1:8b",
            }
        ]
    )

    class _StubProvider:
        def __init__(self, config):
            self.config = config

        async def acompletion_text(self, messages, stream=False, timeout=120):
            return "ok"

    clients = chat_server._build_model_clients(  # noqa: SLF001 - tested internal helper
        settings,
        llm_factory=lambda config: _StubProvider(config),
    )

    assert len(clients) == 1
    assert clients[0].label == "dummy"


@pytest.mark.asyncio
async def test_mcp_rpc_and_event_stream():
    settings = MCPChatSettings(
        models=[
            {
                "name": "dummy",
                "api_type": "ollama",
                "base_url": "http://127.0.0.1:11434/api",
                "api_key": "ollama",
                "model": "llama3.1:8b",
            }
        ]
    )
    app = _build_stub_app(settings)

    server = TestServer(app)
    async with server:
        client = TestClient(server)
        async with client:
            init_rsp = await client.post(
                "/v1/mcp/rpc",
                json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            )
            init_body = await init_rsp.json()
            assert init_rsp.status == 200
            assert init_body["result"]["serverInfo"]["name"] == "metagpt-mcp-chat"

            list_rsp = await client.post(
                "/v1/mcp/rpc",
                json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            )
            list_body = await list_rsp.json()
            assert any(tool["name"] == "chat.send" for tool in list_body["result"]["tools"])

            stream_rsp = await client.get("/v1/mcp/events/stream?session=main&max_events=2")
            event_ingest_rsp = await client.post(
                "/v1/mcp/events",
                json={"session": "main", "event": "x.y", "payload": {"ok": True}},
            )
            assert event_ingest_rsp.status == 202
            stream_text = await stream_rsp.text()
            assert "mcp.stream.ready" in stream_text
            assert "mcp.event.ingested" in stream_text


@pytest.mark.asyncio
async def test_mcp_stdio_bridge_endpoint():
    settings = MCPChatSettings(
        models=[
            {
                "name": "dummy",
                "api_type": "ollama",
                "base_url": "http://127.0.0.1:11434/api",
                "api_key": "ollama",
                "model": "llama3.1:8b",
            }
        ]
    )
    app = _build_stub_app(settings)
    server = TestServer(app)
    async with server:
        client = TestClient(server)
        async with client:
            ndjson_in = "\n".join(
                [
                    json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
                    json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}),
                ]
            )
            rsp = await client.post("/v1/mcp/stdio", data=ndjson_in, headers={"Content-Type": "application/x-ndjson"})
            assert rsp.status == 200
            body = await rsp.text()
            lines = [line for line in body.splitlines() if line.strip()]
            assert len(lines) == 2
            parsed = [json.loads(line) for line in lines]
            assert parsed[0]["result"]["serverInfo"]["name"] == "metagpt-mcp-chat"
            assert "tools" in parsed[1]["result"]
