#!/usr/bin/env python3
"""Redaction transform for sensor payloads.

Input:
  - stdin JSON object
Output:
  - stdout JSON object with common sensitive values replaced by salted tokens
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from typing import Any

SALT = os.environ.get("GENESIS_REDACTION_SALT", "local-dev-salt")

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("PHONE", re.compile(r"\b(?:\+?\d{1,2}\s*)?(?:\(\d{3}\)|\d{3})[-.\s]?\d{3}[-.\s]?\d{4}\b")),
    ("AWS_KEY", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("CARD", re.compile(r"\b(?:\d[ -]*?){13,19}\b")),
]


def token(kind: str, value: str) -> str:
    digest = hashlib.sha256(f"{SALT}:{value}".encode("utf-8")).hexdigest()[:12]
    return f"<<{kind}:{digest}>>"


def redact_text(text: str) -> str:
    out = text
    for kind, pattern in PATTERNS:
        out = pattern.sub(lambda m: token(kind, m.group(0)), out)
    return out


def walk(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [walk(item) for item in value]
    if isinstance(value, dict):
        return {k: walk(v) for k, v in value.items()}
    return value


def main() -> int:
    payload = json.load(sys.stdin)
    redacted = walk(payload)
    json.dump(redacted, sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
