#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json

import duckdb


def rebuild_decisions() -> int:
    out = Path("data/twin/decisions.parquet")
    out.parent.mkdir(parents=True, exist_ok=True)
    md = Path("memory/decisions.md")
    rows = []
    if md.exists():
        for line in md.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("- "):
                rows.append({"situation": line[2:], "options": "[]", "chose": "", "why": "", "outcome_retrospective": ""})
    con = duckdb.connect()
    con.execute("CREATE TABLE t(situation VARCHAR, options VARCHAR, chose VARCHAR, why VARCHAR, outcome_retrospective VARCHAR)")
    for r in rows:
        con.execute("INSERT INTO t VALUES (?, ?, ?, ?, ?)", [r["situation"], r["options"], r["chose"], r["why"], r["outcome_retrospective"]])
    con.execute("COPY t TO ? (FORMAT PARQUET)", [str(out)])
    con.close()
    return len(rows)


if __name__ == "__main__":
    print(json.dumps({"rows": rebuild_decisions()}))
