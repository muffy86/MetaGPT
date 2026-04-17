#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from typing import Any

import httpx

LITELLM_URL = os.environ.get("LITELLM_URL", "http://localhost:4000")
MODEL = os.environ.get("GENESIS_PLANNER_MODEL", "qwen3-coder:30b")


async def rewrite_query(query: str, max_queries: int = 5) -> list[str]:
    payload: dict[str, Any] = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": "Return strict JSON array with query rewrite candidates only.",
            },
            {
                "role": "user",
                "content": (
                    "Produce <=5 retrieval queries: literal query, one HyDE hypothesis, and alternatives. "
                    f"Query: {query}"
                ),
            },
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "extra_body": {"cache_control": {"type": "ephemeral"}},
    }
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.post(f"{LITELLM_URL}/v1/chat/completions", json=payload)
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            arr = parsed.get("queries", [])
        else:
            arr = parsed
        if isinstance(arr, list):
            out = [str(x).strip() for x in arr if str(x).strip()]
            if out:
                return out[:max_queries]
    except Exception:
        pass
    return [query]


if __name__ == "__main__":
    import asyncio
    import sys

    q = " ".join(sys.argv[1:])
    print(json.dumps(asyncio.run(rewrite_query(q))))
