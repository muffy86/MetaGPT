#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Run stdio JSON-RPC MCP bridge for local chat service."""

from metagpt.ext.mcp_chat.bridge_stdio import run_stdio_bridge


if __name__ == "__main__":
    import asyncio
    import os
    from pathlib import Path

    config = Path(os.getenv("MCP_CHAT_CONFIG_PATH", "config/mcp_chat.yaml"))
    raise SystemExit(asyncio.run(run_stdio_bridge(config_path=config)))
