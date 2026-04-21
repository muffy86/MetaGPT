#!/usr/bin/env python3
"""Local-first classifier transform.

Adds `kind`, `tags`, and `sensitivity` with lightweight heuristics first,
optionally upgraded by an Ollama local model call.
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any

import urllib.error
import urllib.request

MODEL = os.environ.get("GENESIS_CLASSIFIER_MODEL", "qwen3-coder:30b")
LITELLM_URL = os.environ.get("LITELLM_URL", "http://localhost:4000/v1/chat/completions")


def heuristic_tags(body: str, title: str) -> tuple[list[str], str]:
    text = f"{title}\n{body}".lower()
    tags: list[str] = []

    if any(x in text for x in ("invoice", "bank", "payment", "wire", "plaid")):
        tags.append("finance")
    if any(x in text for x in ("deadline", "meeting", "calendar", "schedule")):
        tags.append("planning")
    if any(x in text for x in ("token", "wallet", "bridge", "solana", "evm")):
        tags.append("web3")
    if any(x in text for x in ("health", "steps", "sleep", "oura", "whoop")):
        tags.append("health")

    sensitivity = "internal"
    if re.search(r"\b(ssn|passport|private key|seed phrase)\b", text):
        sensitivity = "restricted"
    elif re.search(r"\b(account number|routing|credit card)\b", text):
        sensitivity = "confidential"

    return tags, sensitivity


def local_model_classify(text: str) -> dict[str, Any] | None:
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "Return strict JSON only."},
            {
                "role": "user",
                "content": (
                    "Classify this event into JSON with keys: kind, tags(array), "
                    "sensitivity(public|internal|confidential|restricted). "
                    f"Event:\n{text[:2000]}"
                ),
            },
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1,
        "extra_body": {"cache_control": {"type": "ephemeral"}},
    }
    req = urllib.request.Request(
        LITELLM_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            parsed = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(parsed, dict):
                return parsed
    except (TimeoutError, OSError, json.JSONDecodeError, urllib.error.URLError):
        return None
    return None


def main() -> int:
    payload = json.load(sys.stdin)
    title = str(payload.get("title", ""))
    body = str(payload.get("body", ""))
    tags, sensitivity = heuristic_tags(body, title)

    payload.setdefault("kind", "note")
    payload["tags"] = sorted(set(payload.get("tags", []) + tags))
    payload["sensitivity"] = payload.get("sensitivity", sensitivity)

    llm = local_model_classify(f"title={title}\nbody={body}")
    if llm:
        if isinstance(llm.get("kind"), str) and llm["kind"].strip():
            payload["kind"] = llm["kind"].strip().lower()
        if isinstance(llm.get("tags"), list):
            payload["tags"] = sorted(set(payload.get("tags", []) + [str(t).lower() for t in llm["tags"]]))
        if llm.get("sensitivity") in {"public", "internal", "confidential", "restricted"}:
            payload["sensitivity"] = llm["sensitivity"]

    json.dump(payload, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
