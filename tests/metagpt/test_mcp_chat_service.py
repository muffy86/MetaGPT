#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Unit tests for the hardened MCP chat service."""

from __future__ import annotations

import json
import time

import pytest

from metagpt.ext.mcp_chat.service import (
    MCPChatService,
    ModelClient,
    MultiModelChatEngine,
    SessionStore,
    parse_skill_command,
    sign_payload,
    verify_payload_signature,
)


class _StubLLM:
    def __init__(self, response: str | None = None, error: Exception | None = None):
        self.response = response
        self.error = error

    async def acompletion_text(self, messages, stream=False, timeout=120):
        if self.error:
            raise self.error
        return self.response


@pytest.mark.asyncio
async def test_multimodel_engine_fallback():
    engine = MultiModelChatEngine(
        clients=[
            ModelClient(label="broken", llm=_StubLLM(error=RuntimeError("boom"))),
            ModelClient(label="ok", llm=_StubLLM(response="fallback-response")),
        ]
    )
    text, source = await engine.complete([{"role": "user", "content": "hello"}])
    assert text == "fallback-response"
    assert source == "ok"


def test_signature_roundtrip():
    body = json.dumps({"event": "x", "payload": {"ok": True}}, separators=(",", ":"), sort_keys=True)
    timestamp = str(int(time.time()))
    secret = "unit-test-secret"
    signature = sign_payload(secret=secret, timestamp=timestamp, body=body)

    assert verify_payload_signature(secret=secret, timestamp=timestamp, body=body, signature=signature)
    assert not verify_payload_signature(secret=secret, timestamp=timestamp, body=body + "x", signature=signature)


@pytest.mark.parametrize(
    ("message", "skill", "args"),
    [
        ("/skill web_search {\"query\":\"ai\"}", "web_search", {"query": "ai"}),
        ("/skill text_to_image", "text_to_image", {}),
    ],
)
def test_parse_skill_command_success(message, skill, args):
    got_skill, got_args = parse_skill_command(message)
    assert got_skill == skill
    assert got_args == args


def test_parse_skill_command_invalid_json():
    with pytest.raises(ValueError):
        parse_skill_command('/skill web_search {"query":')


@pytest.mark.asyncio
async def test_service_chat_and_session_snapshot():
    engine = MultiModelChatEngine(
        clients=[ModelClient(label="stub", llm=_StubLLM(response="assistant-reply"))]
    )
    service = MCPChatService(
        engine=engine,
        session_store=SessionStore(),
        declared_skill_names=[],
    )

    result = await service.chat(session_id="main", message="hello world")
    assert result["response"] == "assistant-reply"
    assert result["source"] == "stub"

    snapshot = await service.session_snapshot("main")
    assert snapshot["session"] == "main"
    assert len(snapshot["history"]) == 2
    assert snapshot["history"][0]["role"] == "user"
    assert snapshot["history"][1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_service_skill_allowlist():
    engine = MultiModelChatEngine(
        clients=[ModelClient(label="stub", llm=_StubLLM(response="unused"))]
    )

    async def fake_skill_runner(skill_name: str, args: dict) -> str:
        return f"{skill_name}:{args.get('k', 'none')}"

    service = MCPChatService(
        engine=engine,
        declared_skill_names=["demo_skill"],
        skill_runner=fake_skill_runner,
    )

    success = await service.chat(session_id="s1", message='/skill demo_skill {"k":"v"}')
    assert success["response"] == "demo_skill:v"
    assert success["source"] == "skill:demo_skill"

    with pytest.raises(ValueError):
        await service.chat(session_id="s1", message="/skill unknown_skill {}")


@pytest.mark.asyncio
async def test_stream_chat_completion_chunks():
    engine = MultiModelChatEngine(
        clients=[ModelClient(label="stub", llm=_StubLLM(response="abcdefghij"))]
    )
    service = MCPChatService(engine=engine)
    chunks = []
    async for chunk, source, is_final in service.stream_chat_completion_chunks(
        session_id="stream-session",
        message="stream this",
        chunk_size=3,
    ):
        chunks.append((chunk, source, is_final))

    text_chunks = [c[0] for c in chunks if c[0]]
    assert "".join(text_chunks) == "abcdefghij"
    assert chunks[-1][2] is True
    assert chunks[-1][1] == "stub"


@pytest.mark.asyncio
async def test_mcp_tool_list_and_call():
    engine = MultiModelChatEngine(
        clients=[ModelClient(label="stub", llm=_StubLLM(response="tool-reply"))]
    )
    service = MCPChatService(engine=engine)

    tools = service.list_mcp_tools()
    assert any(tool["name"] == "chat.send" for tool in tools)
    assert any(tool["name"] == "chat.snapshot" for tool in tools)
    assert any(tool["name"] == "mcp.event.ingest" for tool in tools)

    sent = await service.call_mcp_tool(
        "chat.send",
        {"session": "tool-main", "message": "hello via tool"},
    )
    assert sent["response"] == "tool-reply"

    snap = await service.call_mcp_tool("chat.snapshot", {"session": "tool-main"})
    assert snap["session"] == "tool-main"
    assert len(snap["history"]) == 2
