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

    async def chat(self, session_id: str, message: str, preferred_models=None, metadata=None):
        history = self._sessions.setdefault(session_id, [])
        reply = f"echo:{message}"
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": reply})
        return {"session": session_id, "source": "stub", "message": message, "response": reply}

    async def session_snapshot(self, session_id: str):
        return {"session": session_id, "history": self._sessions.get(session_id, [])}

    async def ingest_mcp_event(self, session_id: str, event: str, payload: dict):
        return {"status": "accepted", "session": session_id, "event": event, "payload": payload}


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
