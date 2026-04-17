from __future__ import annotations

from datetime import datetime, timezone


def run(payload: dict) -> dict:
    return {
        "trigger": "triage_inbox",
        "ts": datetime.now(tz=timezone.utc).isoformat(),
        "status": "ok",
        "payload": payload,
    }
