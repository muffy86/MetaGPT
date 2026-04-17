#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=["jsonl", "parquet", "markdown"], default="jsonl")
    parser.add_argument("--include-restricted", action="store_true")
    parser.add_argument("--out", default="runs/export")
    args = parser.parse_args()

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect("data/ledger.duckdb")
    where = "" if args.include_restricted else "WHERE sensitivity IN ('public','internal')"
    rows = conn.execute(f"SELECT id, ts, source, kind, actor, title, body, sensitivity FROM exocortex.events {where} ORDER BY ts DESC").fetchall()
    conn.close()

    if args.format == "jsonl":
        out = Path(f"{args.out}.jsonl")
        with out.open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps({"id": r[0], "ts": str(r[1]), "source": r[2], "kind": r[3], "actor": r[4], "title": r[5], "body": r[6], "sensitivity": r[7]}) + "\n")
    elif args.format == "parquet":
        out = Path(f"{args.out}.parquet")
        c = duckdb.connect()
        c.execute("CREATE TABLE t AS SELECT * FROM read_json_auto(?)", [json.dumps([{"id": r[0], "ts": str(r[1]), "source": r[2], "kind": r[3], "actor": r[4], "title": r[5], "body": r[6], "sensitivity": r[7]} for r in rows])])
        c.execute("COPY t TO ? (FORMAT PARQUET)", [str(out)])
        c.close()
    else:
        out = Path(f"{args.out}.md")
        lines = ["# Exocortex Export", ""]
        for r in rows[:5000]:
            lines.append(f"- [{r[1]}] {r[2]}/{r[3]} {r[5]} ({r[0]})")
        out.write_text("\n".join(lines), encoding="utf-8")

    print(f"exported {len(rows)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
