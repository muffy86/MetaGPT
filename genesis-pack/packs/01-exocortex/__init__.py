from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json

import duckdb
from ulid import ULID

DB_PATH = Path("data/ledger.duckdb")


def _conn() -> duckdb.DuckDBPyConnection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(DB_PATH))


@dataclass(slots=True)
class Event:
    id: str
    ts: datetime
    source: str
    kind: str
    actor: str
    body: str
    meta: dict[str, Any]


def append_event(source: str, kind: str, body: str, meta: dict[str, Any], ts: datetime | None = None, actor: str = "self") -> str:
    event_id = str(ULID())
    now = ts or datetime.now(tz=timezone.utc)
    title = str(meta.get("title", ""))
    subjects = meta.get("subjects", [])
    sensitivity = str(meta.get("sensitivity", "internal"))
    conn = _conn()
    conn.execute(
        """
        CREATE SCHEMA IF NOT EXISTS exocortex;
        CREATE TABLE IF NOT EXISTS exocortex.events (
          id VARCHAR PRIMARY KEY,
          ts TIMESTAMPTZ,
          source VARCHAR,
          kind VARCHAR,
          actor VARCHAR,
          subjects JSON,
          title VARCHAR,
          body VARCHAR,
          body_hash VARCHAR,
          meta JSON,
          sensitivity VARCHAR DEFAULT 'internal',
          ingested_at TIMESTAMPTZ DEFAULT now(),
          embed_ref VARCHAR
        );
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO exocortex.events
        (id, ts, source, kind, actor, subjects, title, body, body_hash, meta, sensitivity)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, sha256(?), ?, ?)
        """,
        [event_id, now, source, kind, actor, json.dumps(subjects), title, body, body, json.dumps(meta), sensitivity],
    )
    conn.close()
    return event_id
