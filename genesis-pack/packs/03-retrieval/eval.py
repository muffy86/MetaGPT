#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from api import retrieve


def load_queries(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


async def run_eval(path: Path, quick: bool = False) -> dict:
    queries = load_queries(path)
    if quick:
        queries = queries[:5]
    if not queries:
        return {"total": 0, "recall_at_10": 1.0}

    hits = 0
    for q in queries:
        expected = set(q.get("expects", []))
        results = await retrieve(q["query"], k=10)
        got = {h.event_id for h in results}
        if expected.intersection(got):
            hits += 1
    total = len(queries)
    return {"total": total, "recall_at_10": hits / total if total else 1.0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", default="packs/03-retrieval/fixtures/queries.jsonl")
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()
    result = asyncio.run(run_eval(Path(args.fixtures), quick=args.quick))
    print(json.dumps(result))
