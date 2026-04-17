#!/usr/bin/env python3
"""Entity/date/amount extraction transform."""

from __future__ import annotations

import json
import re
import sys

MONEY_RE = re.compile(r"\$?\b\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b")
DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
ENTITY_RE = re.compile(r"\b[A-Z][a-zA-Z]{2,}(?:\s+[A-Z][a-zA-Z]{2,})*\b")


def main() -> int:
    payload = json.load(sys.stdin)
    text = f"{payload.get('title', '')}\n{payload.get('body', '')}"

    amounts = MONEY_RE.findall(text)[:20]
    dates = DATE_RE.findall(text)[:20]
    entities = [e for e in ENTITY_RE.findall(text) if len(e) <= 64][:40]

    payload.setdefault("meta", {})
    payload["meta"]["amounts"] = amounts
    payload["meta"]["dates"] = dates
    payload["meta"]["entities"] = entities

    json.dump(payload, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
