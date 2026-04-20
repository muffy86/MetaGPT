#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Run the hardened MCP chat server."""

import metagpt.provider  # noqa: F401  # Ensure provider registry is initialized.

from metagpt.ext.mcp_chat.server import run_server


if __name__ == "__main__":
    run_server()
