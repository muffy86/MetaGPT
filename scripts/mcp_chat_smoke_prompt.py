#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Prompt-based smoke test for the MCP chat server."""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any, Dict

import aiohttp


async def call_json(session: aiohttp.ClientSession, method: str, url: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    async with session.request(method, url, json=payload) as response:
        text = await response.text()
        if response.status >= 400:
            raise RuntimeError(f"{method} {url} failed ({response.status}): {text}")
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"{method} {url} returned non-JSON: {text}") from exc


async def main(base_url: str, session_id: str, prompt: str) -> None:
    async with aiohttp.ClientSession() as session:
        health = await call_json(session, "GET", f"{base_url}/health")
        print("health:", json.dumps(health, ensure_ascii=False))

        result = await call_json(
            session,
            "POST",
            f"{base_url}/chat",
            {"session": session_id, "message": prompt},
        )
        print("chat:", json.dumps(result, ensure_ascii=False))

        snapshot = await call_json(session, "GET", f"{base_url}/chat?session={session_id}")
        print("snapshot:", json.dumps(snapshot, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run MCP chat smoke prompt against local server.")
    parser.add_argument("--base-url", default="http://127.0.0.1:18789")
    parser.add_argument("--session", default="main")
    parser.add_argument(
        "--prompt",
        default="Provide a short hardening checklist for multi-model chat services.",
    )
    args = parser.parse_args()
    asyncio.run(main(args.base_url, args.session, args.prompt))
