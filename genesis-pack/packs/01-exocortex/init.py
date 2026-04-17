#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import duckdb

DB_PATH = Path("data/ledger.duckdb")


def main() -> int:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(DB_PATH))
    conn.execute("CREATE SCHEMA IF NOT EXISTS exocortex")
    conn.execute(
        """
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
        )
        """
    )
    conn.execute("CREATE TABLE IF NOT EXISTS exocortex.events_embed (id VARCHAR, source VARCHAR, ts TIMESTAMPTZ, title VARCHAR, body VARCHAR, actor VARCHAR, vec JSON)")
    conn.execute("CREATE TABLE IF NOT EXISTS exocortex.graph_events (event_id VARCHAR, entity VARCHAR, rel VARCHAR, from_ts TIMESTAMPTZ, to_ts TIMESTAMPTZ)")
    conn.close()
    Path("data/exocortex/graph.kuzu").parent.mkdir(parents=True, exist_ok=True)
    Path("memory/identity.md").parent.mkdir(parents=True, exist_ok=True)
    if not Path("memory/identity.md").exists():
        Path("memory/identity.md").write_text("# Identity\ntimezone: UTC\n", encoding="utf-8")
    print("exocortex init complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
