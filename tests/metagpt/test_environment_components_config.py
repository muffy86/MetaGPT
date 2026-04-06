#!/usr/bin/env python
# -*- coding: utf-8 -*-

from metagpt.config2 import Config
from tests.metagpt.provider.mock_llm_config import mock_llm_config


def test_environment_components_default_sections():
    cfg = Config(llm=mock_llm_config)

    assert cfg.mcp is not None
    assert cfg.rag is not None
    assert cfg.connectors is not None
    assert cfg.skills is not None
    assert cfg.tools is not None
    assert cfg.access is not None
    assert cfg.automation is not None


def test_environment_components_can_be_configured():
    cfg = Config(
        llm=mock_llm_config,
        mcp={
            "enabled": True,
            "default_server": "local",
            "servers": {
                "local": {
                    "enabled": True,
                    "transport": "stdio",
                    "command": "python",
                    "args": ["-m", "mock_mcp_server"],
                }
            },
        },
        rag={"enabled": True, "retriever": "bm25", "ranker": "none", "top_k": 3},
        connectors={
            "enabled": True,
            "default_connector": "github",
            "items": {
                "github": {
                    "enabled": True,
                    "provider": "github",
                    "endpoint": "https://api.github.com",
                    "auth_type": "bearer",
                    "auth_env": "GITHUB_TOKEN",
                }
            },
        },
        skills={"enabled": True, "runtime_mode": "on_demand"},
        tools={"enabled": True, "execution_mode": "allow_all"},
        access={"enabled": True, "default_policy": "allow", "allow_shell": False},
        automation={
            "enabled": True,
            "jobs": {
                "daily_sync": {
                    "enabled": True,
                    "trigger": {"enabled": True, "type": "schedule", "schedule": "0 2 * * *"},
                    "workflow": ["connectors.sync:github", "rag.index:update"],
                }
            },
        },
    )

    assert cfg.mcp.enabled is True
    assert cfg.mcp.default_server == "local"
    assert "local" in cfg.mcp.servers
    assert cfg.rag.enabled is True
    assert cfg.rag.top_k == 3
    assert cfg.connectors.enabled is True
    assert cfg.connectors.default_connector == "github"
    assert "github" in cfg.connectors.items
    assert cfg.skills.runtime_mode.value == "on_demand"
    assert cfg.tools.execution_mode.value == "allow_all"
    assert cfg.access.enabled is True
    assert cfg.automation.enabled is True
    assert "daily_sync" in cfg.automation.jobs

