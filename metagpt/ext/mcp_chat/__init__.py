#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""MCP chat extension package."""

from typing import Any

__all__ = ["create_app", "run_server", "run_stdio_bridge"]


def create_app(*args: Any, **kwargs: Any):
    from metagpt.ext.mcp_chat.server import create_app as _create_app

    return _create_app(*args, **kwargs)


def run_server(*args: Any, **kwargs: Any):
    from metagpt.ext.mcp_chat.server import run_server as _run_server

    return _run_server(*args, **kwargs)


def run_stdio_bridge(*args: Any, **kwargs: Any):
    from metagpt.ext.mcp_chat.bridge_stdio import run_stdio_bridge as _run_stdio_bridge

    return _run_stdio_bridge(*args, **kwargs)
