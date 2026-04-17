#!/usr/bin/env python3
from __future__ import annotations

import json
import sys


def handle(event: dict) -> dict:
    action = event.get("action", "noop")
    return {"ok": True, "action": action, "status": "queued"}


if __name__ == "__main__":
    payload = json.loads(sys.stdin.read() or "{}")
    print(json.dumps(handle(payload)))
