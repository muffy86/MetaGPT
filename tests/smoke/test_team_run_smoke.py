#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest

from metagpt.context import Context
from metagpt.roles.role import Role
from metagpt.team import Team
from metagpt.actions.action import Action


class StubLLM:
    """Minimal async LLM stub used to keep tests offline and deterministic."""

    def __init__(self):
        self.system_prompt = ""
        self.cost_manager = None
        self.called = False

    async def aask(self, *_args, **_kwargs):
        self.called = True
        return ""


class StaticReply(Action):
    """Simple action that echoes a fixed acknowledgement without invoking an LLM."""

    async def run(self, *_args, **_kwargs):
        return "ACK"


class DummyRole(Role):
    """Role that reacts once with a static acknowledgement."""

    def __init__(self, stub_llm: StubLLM):
        super().__init__(name="Echo", profile="listener", goal="acknowledge requirements")
        self.llm = stub_llm
        self.set_actions([StaticReply])
        self.stub_llm = stub_llm


@pytest.mark.asyncio
async def test_team_run_stub_pipeline(monkeypatch):
    """Exercise Team.run with a deterministic role to map the orchestration surface."""

    stub_llm = StubLLM()

    def _patched_llm(self: Context):
        stub_llm.cost_manager = self.cost_manager
        return stub_llm

    def _patched_llm_with_config(self: Context, _llm_config):
        stub_llm.cost_manager = self._select_costmanager(_llm_config)
        return stub_llm

    monkeypatch.setattr(Context, "llm", _patched_llm)
    monkeypatch.setattr(Context, "llm_with_cost_manager_from_llm_config", _patched_llm_with_config)

    context = Context()
    team = Team(context=context, use_mgx=False)
    team.invest(1.0)
    team.hire([DummyRole(stub_llm)])

    history = await team.run(n_round=1, idea="Ship a static acknowledgement", auto_archive=False)
    messages = history.get()

    assert history.count() == 2, "Expect initial requirement plus the role acknowledgement"
    assert messages[0].content == "Ship a static acknowledgement"
    assert any(msg.content == "ACK" for msg in messages)
    assert not stub_llm.called, "Stub LLM should remain unused in the deterministic pipeline"
