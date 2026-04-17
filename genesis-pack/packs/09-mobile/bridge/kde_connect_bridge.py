#!/usr/bin/env python3
"""KDE Connect bridge for Android edge ingestion.

This module mirrors Android SMS/notification payloads into the shared events shape
used by Pack 02, allowing one ingestion path regardless of client platform.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import uuid
from typing import Any


@dataclass(slots=True)
class AndroidEvent:
    id: str
    ts: float
    source: str
    kind: str
    actor: str
    subjects: list[str]
    title: str
    body: str
    thread_id: str | None = None
    meta: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "ts": self.ts,
            "source": self.source,
            "kind": self.kind,
            "actor": self.actor,
            "subjects": self.subjects,
            "title": self.title,
            "body": self.body,
            "thread_id": self.thread_id,
            "meta": self.meta or {},
        }


def normalize_sms(payload: dict[str, Any]) -> AndroidEvent:
    return AndroidEvent(
        id=str(uuid.uuid4()),
        ts=float(payload.get("ts") or datetime.now(tz=timezone.utc).timestamp()),
        source="sms",
        kind="message",
        actor=str(payload.get("from") or "unknown"),
        subjects=[str(payload.get("from") or "unknown")],
        title=str(payload.get("thread") or "sms"),
        body=str(payload.get("body") or ""),
        thread_id=str(payload.get("thread_id") or payload.get("from") or ""),
        meta={"platform": "android", "transport": "kde-connect"},
    )


def normalize_clipboard(payload: dict[str, Any]) -> AndroidEvent:
    return AndroidEvent(
        id=str(uuid.uuid4()),
        ts=float(payload.get("ts") or datetime.now(tz=timezone.utc).timestamp()),
        source="clipboard",
        kind="clipboard",
        actor="self",
        subjects=["self"],
        title="android clipboard",
        body=str(payload.get("text") or ""),
        thread_id=None,
        meta={"platform": "android", "app": payload.get("app")},
    )


def main() -> int:
    message = json.load(open(0))  # stdin
    kind = message.get("type")
    if kind == "sms":
        out = normalize_sms(message)
    else:
        out = normalize_clipboard(message)
    json.dump(out.as_dict(), open(1, "w"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
