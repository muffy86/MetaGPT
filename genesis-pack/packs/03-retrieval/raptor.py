#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import duckdb
from ulid import ULID


def build_rollups(period: str = "week") -> int:
    db = Path("data/ledger.duckdb")
    if not db.exists():
        return 0
    con = duckdb.connect(str(db))
    rows = con.execute(
        """
        SELECT source, date_trunc(?, ts) AS bucket, COUNT(*) AS n,
               string_agg(coalesce(title, ''), '\n' ORDER BY ts DESC) AS notes
        FROM exocortex.events
        GROUP BY 1,2
        """,
        [period],
    ).fetchall()
    inserted = 0
    for source, bucket, n, notes in rows:
        summary = f"{period} summary for {source}: {n} events.\n{(notes or '')[:1800]}"
        con.execute(
            """
            INSERT OR REPLACE INTO exocortex.events
            (id, ts, source, kind, actor, subjects, title, body, body_hash, meta, sensitivity)
            VALUES (?, ?, 'retrieval', 'summary:raptor', 'self', '[]', ?, ?, sha256(?), '{}', 'internal')
            """,
            [str(ULID()), datetime.now(tz=timezone.utc), f"RAPTOR {period} {source} {bucket}", summary, summary],
        )
        inserted += 1
    con.close()
    return inserted


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--period", default="week", choices=["week", "month", "quarter"])
    args = parser.parse_args()
    print(build_rollups(args.period))
