#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Hardened multi-model chat service with webhook and skill extensions."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, List, Optional, Sequence, Tuple

import aiohttp
import yaml
from metagpt.const import METAGPT_ROOT
from metagpt.logs import logger

DEFAULT_SYSTEM_PROMPT = (
    "You are MetaGPT MCP Chat. Be concise, safe, and reliable. "
    "Prefer deterministic answers when asked for operational instructions."
)
MAX_SIGNATURE_SKEW_SECONDS = 300


def _json_dumps(data: Dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def sign_payload(secret: str, timestamp: str, body: str) -> str:
    payload = f"{timestamp}.{body}".encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_payload_signature(
    secret: str,
    timestamp: str,
    body: str,
    signature: str,
    tolerance_seconds: int = MAX_SIGNATURE_SKEW_SECONDS,
) -> bool:
    if not secret or not timestamp or not signature:
        return False
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    if abs(int(time.time()) - ts) > tolerance_seconds:
        return False
    expected = sign_payload(secret=secret, timestamp=timestamp, body=body)
    return hmac.compare_digest(expected, signature)


@dataclass
class ResourcePack:
    name: str
    content: str


def load_resource_packs(pack_dir: Path) -> List[ResourcePack]:
    if not pack_dir.exists() or not pack_dir.is_dir():
        logger.warning(f"Resource pack directory not found: {pack_dir}")
        return []
    packs: List[ResourcePack] = []
    for path in sorted(pack_dir.glob("*.md")):
        content = path.read_text(encoding="utf-8").strip()
        if content:
            packs.append(ResourcePack(name=path.stem, content=content))
    return packs


def compose_system_prompt(base_prompt: str, packs: Sequence[ResourcePack]) -> str:
    sections = [base_prompt.strip()]
    for pack in packs:
        sections.append(f"[Resource Pack: {pack.name}]\n{pack.content}")
    return "\n\n".join(section for section in sections if section)


def load_declared_skill_names(skills_yaml: Optional[Path] = None) -> List[str]:
    target = skills_yaml or (METAGPT_ROOT / "docs/.well-known/skills.yaml")
    if not target.exists():
        logger.warning(f"Skills declaration not found: {target}")
        return []

    data = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    assistant = (data.get("entities") or {}).get("Assistant") or {}
    raw_skills = assistant.get("skills") or []
    names: List[str] = []
    for item in raw_skills:
        name = item.get("name")
        if isinstance(name, str) and name:
            names.append(name)
    return names


def parse_skill_command(message: str) -> Tuple[Optional[str], Dict[str, Any]]:
    text = message.strip()
    if not text.startswith("/skill "):
        return None, {}

    command = text[len("/skill ") :].strip()
    if not command:
        raise ValueError("Skill command is empty. Use: /skill <name> {json-args}")

    parts = command.split(maxsplit=1)
    skill_name = parts[0]
    args: Dict[str, Any] = {}
    if len(parts) > 1:
        try:
            parsed = json.loads(parts[1])
        except json.JSONDecodeError as exc:
            raise ValueError(f"Skill arguments must be valid JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise ValueError("Skill arguments must decode to a JSON object")
        args = parsed
    return skill_name, args


@dataclass
class ModelClient:
    label: str
    llm: Any


class EventBroker:
    """Fan-out event broker used by SSE and bridge transports."""

    def __init__(self, max_queue_size: int = 256):
        self.max_queue_size = max_queue_size
        self._subscribers: Dict[int, Tuple[Optional[str], asyncio.Queue]] = {}
        self._next_subscription_id = 1
        self._lock = asyncio.Lock()

    async def subscribe(self, session_id: Optional[str] = None) -> Tuple[int, asyncio.Queue]:
        queue: asyncio.Queue = asyncio.Queue(maxsize=self.max_queue_size)
        async with self._lock:
            subscription_id = self._next_subscription_id
            self._next_subscription_id += 1
            self._subscribers[subscription_id] = (session_id, queue)
        return subscription_id, queue

    async def unsubscribe(self, subscription_id: int) -> None:
        async with self._lock:
            self._subscribers.pop(subscription_id, None)

    async def publish(self, event: Dict[str, Any]) -> None:
        async with self._lock:
            subscribers = list(self._subscribers.items())
        for _, (session_filter, queue) in subscribers:
            if session_filter and session_filter != event.get("session"):
                continue
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                # Drop event if queue remains full after one eviction.
                continue


class MultiModelChatEngine:
    """Runs model calls with deterministic fallback ordering."""

    def __init__(self, clients: Sequence[ModelClient], timeout_seconds: int = 120):
        if not clients:
            raise ValueError("At least one model client must be configured")
        self.clients: List[ModelClient] = list(clients)
        self.timeout_seconds = timeout_seconds

    def list_models(self) -> List[str]:
        return [client.label for client in self.clients]

    def _order_clients(self, preferred_models: Optional[Sequence[str]]) -> List[ModelClient]:
        if not preferred_models:
            return self.clients
        rank = {name: ix for ix, name in enumerate(preferred_models)}
        return sorted(
            self.clients,
            key=lambda client: rank.get(client.label, len(rank)),
        )

    async def complete(
        self,
        messages: List[Dict[str, str]],
        preferred_models: Optional[Sequence[str]] = None,
    ) -> Tuple[str, str]:
        errors: List[str] = []
        for client in self._order_clients(preferred_models):
            try:
                text = await client.llm.acompletion_text(
                    messages,
                    stream=False,
                    timeout=self.timeout_seconds,
                )
                if not isinstance(text, str) or not text.strip():
                    raise RuntimeError("Model returned empty response")
                return text, client.label
            except Exception as exc:
                errors.append(f"{client.label}: {exc.__class__.__name__}")
                logger.warning(f"Model {client.label} failed: {exc}")
        raise RuntimeError(f"All configured models failed: {'; '.join(errors)}")


class SessionStore:
    """In-memory chat session state with bounded history."""

    def __init__(self, max_messages: int = 48):
        self.max_messages = max_messages
        self._sessions: Dict[str, List[Dict[str, str]]] = {}
        self._lock = asyncio.Lock()

    async def get(self, session_id: str) -> List[Dict[str, str]]:
        async with self._lock:
            return [dict(item) for item in self._sessions.get(session_id, [])]

    async def append_turn(self, session_id: str, user_message: str, assistant_message: str) -> None:
        async with self._lock:
            history = self._sessions.setdefault(session_id, [])
            history.append({"role": "user", "content": user_message})
            history.append({"role": "assistant", "content": assistant_message})
            del history[: max(0, len(history) - self.max_messages)]

    async def append_system_event(self, session_id: str, event_note: str) -> None:
        async with self._lock:
            history = self._sessions.setdefault(session_id, [])
            history.append({"role": "system", "content": event_note})
            del history[: max(0, len(history) - self.max_messages)]


class WebhookDispatcher:
    """Sends signed webhook notifications for audit integrations."""

    def __init__(self, url: Optional[str] = None, secret: Optional[str] = None, timeout_seconds: int = 10):
        self.url = (url or "").strip()
        self.secret = (secret or "").strip()
        self.timeout_seconds = timeout_seconds

    async def emit(self, event: str, payload: Dict[str, Any]) -> None:
        if not self.url:
            return

        body_obj = {"event": event, **payload}
        body = _json_dumps(body_obj)
        headers = {"Content-Type": "application/json"}
        if self.secret:
            timestamp = str(int(time.time()))
            headers["X-MetaGPT-Timestamp"] = timestamp
            headers["X-MetaGPT-Signature"] = sign_payload(self.secret, timestamp, body)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.url,
                    data=body.encode("utf-8"),
                    headers=headers,
                    timeout=self.timeout_seconds,
                ) as response:
                    if response.status >= 400:
                        logger.warning(f"Webhook delivery failed with status={response.status}")
        except Exception as exc:
            logger.warning(f"Webhook delivery error: {exc}")


class MCPChatService:
    """Core orchestration for chat, skills, and MCP webhook events."""

    def __init__(
        self,
        engine: MultiModelChatEngine,
        session_store: Optional[SessionStore] = None,
        webhook_dispatcher: Optional[WebhookDispatcher] = None,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        declared_skill_names: Optional[Sequence[str]] = None,
        max_message_chars: int = 8000,
        skill_runner: Optional[Callable[[str, Dict[str, Any]], Awaitable[str]]] = None,
        event_broker: Optional[EventBroker] = None,
    ):
        self.engine = engine
        self.sessions = session_store or SessionStore()
        self.webhooks = webhook_dispatcher or WebhookDispatcher()
        self.system_prompt = system_prompt
        self.max_message_chars = max_message_chars
        self.declared_skill_names = set(declared_skill_names or [])
        self._skill_runner = skill_runner or self._default_skill_runner
        self.events = event_broker or EventBroker()

    async def _default_skill_runner(self, skill_name: str, args: Dict[str, Any]) -> str:
        from metagpt.actions.skill_action import SkillAction

        return await SkillAction.find_and_call_function(skill_name, args)

    async def _run_skill(self, skill_name: str, args: Dict[str, Any]) -> str:
        if self.declared_skill_names and skill_name not in self.declared_skill_names:
            raise ValueError(
                f"Unknown skill '{skill_name}'. Allowed skills: {', '.join(sorted(self.declared_skill_names))}"
            )
        result = await self._skill_runner(skill_name, args)
        return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)

    async def chat(
        self,
        session_id: str,
        message: str,
        preferred_models: Optional[Sequence[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        clean_message = message.strip()
        if not clean_message:
            raise ValueError("Message cannot be empty")
        if len(clean_message) > self.max_message_chars:
            raise ValueError(f"Message exceeds max length ({self.max_message_chars} chars)")

        skill_name, skill_args = parse_skill_command(clean_message)
        if skill_name:
            answer = await self._run_skill(skill_name, skill_args)
            source = f"skill:{skill_name}"
        else:
            history = await self.sessions.get(session_id)
            model_messages = [{"role": "system", "content": self.system_prompt}, *history]
            model_messages.append({"role": "user", "content": clean_message})
            answer, source = await self.engine.complete(model_messages, preferred_models)

        await self.sessions.append_turn(session_id=session_id, user_message=clean_message, assistant_message=answer)
        await self.webhooks.emit(
            event="chat.completed",
            payload={
                "session": session_id,
                "source": source,
                "message": clean_message,
                "response": answer,
                "metadata": metadata or {},
            },
        )
        await self.events.publish(
            {
                "type": "chat.completed",
                "session": session_id,
                "source": source,
                "message": clean_message,
                "response": answer,
                "metadata": metadata or {},
            }
        )

        return {
            "session": session_id,
            "source": source,
            "message": clean_message,
            "response": answer,
        }

    async def session_snapshot(self, session_id: str) -> Dict[str, Any]:
        history = await self.sessions.get(session_id)
        return {"session": session_id, "history": history}

    async def ingest_mcp_event(self, session_id: str, event: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        note = f"[mcp-event:{event}] {json.dumps(payload, ensure_ascii=False, sort_keys=True)}"
        await self.sessions.append_system_event(session_id=session_id, event_note=note)
        await self.webhooks.emit(
            event="mcp.event.ingested",
            payload={"session": session_id, "event": event, "payload": payload},
        )
        await self.events.publish(
            {
                "type": "mcp.event.ingested",
                "session": session_id,
                "event": event,
                "payload": payload,
            }
        )
        return {"status": "accepted", "session": session_id, "event": event}

    async def open_event_subscription(self, session_id: Optional[str] = None) -> Tuple[int, asyncio.Queue]:
        return await self.events.subscribe(session_id=session_id)

    async def close_event_subscription(self, subscription_id: int) -> None:
        await self.events.unsubscribe(subscription_id)

    def list_mcp_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "chat.send",
                "description": "Send a chat message to a session.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "session": {"type": "string"},
                        "message": {"type": "string"},
                        "preferred_models": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["message"],
                },
            },
            {
                "name": "chat.snapshot",
                "description": "Fetch chat history for a session.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"session": {"type": "string"}},
                },
            },
            {
                "name": "mcp.event.ingest",
                "description": "Ingest an MCP event into session memory.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "session": {"type": "string"},
                        "event": {"type": "string"},
                        "payload": {"type": "object"},
                    },
                    "required": ["event", "payload"],
                },
            },
        ]

    async def call_mcp_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        args = arguments or {}
        if not isinstance(args, dict):
            raise ValueError("Tool arguments must be a JSON object")

        if name == "chat.send":
            message = args.get("message")
            if not isinstance(message, str):
                raise ValueError("chat.send requires string argument `message`")
            session_id = str(args.get("session", "main"))
            preferred_models = args.get("preferred_models")
            if preferred_models is not None and not isinstance(preferred_models, list):
                raise ValueError("chat.send preferred_models must be an array of strings")
            return await self.chat(
                session_id=session_id,
                message=message,
                preferred_models=preferred_models,
                metadata={"transport": "mcp-tool"},
            )

        if name == "chat.snapshot":
            session_id = str(args.get("session", "main"))
            return await self.session_snapshot(session_id)

        if name == "mcp.event.ingest":
            event = args.get("event")
            payload = args.get("payload")
            if not isinstance(event, str) or not event:
                raise ValueError("mcp.event.ingest requires non-empty string argument `event`")
            if not isinstance(payload, dict):
                raise ValueError("mcp.event.ingest requires object argument `payload`")
            session_id = str(args.get("session", "main"))
            return await self.ingest_mcp_event(session_id=session_id, event=event, payload=payload)

        raise ValueError(f"Unknown tool '{name}'")

    async def stream_chat_completion_chunks(
        self,
        session_id: str,
        message: str,
        preferred_models: Optional[Sequence[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_size: int = 64,
    ) -> AsyncIterator[Tuple[str, str, bool]]:
        result = await self.chat(
            session_id=session_id,
            message=message,
            preferred_models=preferred_models,
            metadata=metadata,
        )
        text = result["response"]
        source = result["source"]
        if not text:
            yield "", source, True
            return
        size = max(1, chunk_size)
        for ix in range(0, len(text), size):
            yield text[ix : ix + size], source, False
        yield "", source, True
