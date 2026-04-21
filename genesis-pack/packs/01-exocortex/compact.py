#!/usr/bin/env python3
from __future__ import annotations

import duckdb


def main() -> int:
    conn = duckdb.connect("data/ledger.duckdb")
    conn.execute("DELETE FROM exocortex.events_embed WHERE id NOT IN (SELECT id FROM exocortex.events)")
    conn.execute("VACUUM")
    conn.close()
    print("compaction complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
