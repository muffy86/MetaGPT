#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""JSON-RPC stdio MCP bridge for MCPChatService."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from metagpt.ext.mcp_chat.server import MCPChatSettings, build_service


def _mcp_response(req_id: Any, result: Any) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _mcp_error(req_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


async def _handle_request(service, request_obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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

    is_notification = req_id is None
    try:
        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "metagpt-mcp-chat-stdio", "version": "0.1.0"},
                "capabilities": {"tools": {"listChanged": False}},
            }
            return None if is_notification else _mcp_response(req_id, result)
        if method in {"ping"}:
            return None if is_notification else _mcp_response(req_id, {})
        if method in {"tools/list", "tools.list"}:
            return None if is_notification else _mcp_response(req_id, {"tools": service.list_mcp_tools()})
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
        return _mcp_error(req_id, -32601, f"Method not found: {method}")
    except ValueError as exc:
        return _mcp_error(req_id, -32602, str(exc))
    except Exception as exc:
        return _mcp_error(req_id, -32000, f"Server error: {exc}")


async def run_stdio_bridge(config_path: Optional[Path] = None) -> int:
    settings = MCPChatSettings.load(config_path=config_path)
    service = build_service(settings)

    while True:
        line = await asyncio.to_thread(sys.stdin.buffer.readline)
        if not line:
            return 0
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            sys.stdout.write(json.dumps(_mcp_error(None, -32700, "Parse error"), ensure_ascii=False) + "\n")
            sys.stdout.flush()
            continue

        if isinstance(payload, list):
            responses = []
            for item in payload:
                if not isinstance(item, dict):
                    responses.append(_mcp_error(None, -32600, "Invalid Request"))
                    continue
                resp = await _handle_request(service, item)
                if resp is not None:
                    responses.append(resp)
            if responses:
                sys.stdout.write(json.dumps(responses, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            continue

        if not isinstance(payload, dict):
            sys.stdout.write(json.dumps(_mcp_error(None, -32600, "Invalid Request"), ensure_ascii=False) + "\n")
            sys.stdout.flush()
            continue

        resp = await _handle_request(service, payload)
        if resp is None:
            continue
        sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run MCP stdio bridge for MetaGPT chat service")
    parser.add_argument(
        "--config",
        default=os.getenv("MCP_CHAT_CONFIG_PATH", str(Path("config/mcp_chat.yaml"))),
        help="Path to MCP chat YAML config",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run_stdio_bridge(Path(args.config))))
