#!/usr/bin/env python3
"""Batch embedding transform writing vectors to LanceDB-ready JSONL.

This script is intentionally format-simple so it can run in streaming mode:
- stdin: one JSON object per line
- stdout: one enriched JSON object per line, each with `embedding`
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

MODEL = os.environ.get("GENESIS_EMBED_MODEL", "bge-m3")
LITELLM_URL = os.environ.get("LITELLM_EMBED_URL", "http://localhost:4000/v1/embeddings")


def embed(text: str) -> list[float]:
    payload = {"model": MODEL, "input": text[:4000]}
    req = urllib.request.Request(
        LITELLM_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            vector = None
            if isinstance(data.get("data"), list) and data["data"]:
                vector = data["data"][0].get("embedding")
            if isinstance(vector, list):
                return [float(x) for x in vector]
    except (TimeoutError, OSError, ValueError, json.JSONDecodeError, urllib.error.URLError):
        pass
    return []


def main() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        payload = json.loads(line)
        text = f"{payload.get('title', '')}\n{payload.get('body', '')}".strip()
        payload["embedding"] = embed(text)
        sys.stdout.write(json.dumps(payload) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
