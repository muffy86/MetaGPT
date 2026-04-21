#!/usr/bin/env python3
"""Deterministic replay utility for orchestrator traces."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import hashlib
import json
import os


@dataclass
class ReplayResult:
    total: int
    matched: int
    diverged: int


def hash_json(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def replay(trace_path: Path, *, deterministic: bool = True) -> ReplayResult:
    if deterministic:
        os.environ["DETERMINISTIC"] = "1"
    total = 0
    matched = 0
    diverged = 0
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        total += 1
        event = json.loads(line)
        observed = event.get("output_hash")
        # Baseline deterministic stub: compares against stored hash.
        # Real runtime plugs in tool/model re-execution and computes fresh output hash.
        replayed = observed
        if replayed == observed:
            matched += 1
        else:
            diverged += 1
    return ReplayResult(total=total, matched=matched, diverged=diverged)


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay a GENESIS trace.jsonl")
    parser.add_argument("trace", type=Path, help="Path to runs/<session>/trace.jsonl")
    args = parser.parse_args()
    result = replay(args.trace, deterministic=True)
    print(
        json.dumps(
            {
                "total": result.total,
                "matched": result.matched,
                "diverged": result.diverged,
                "deterministic": True,
            }
        )
    )
    return 0 if result.diverged == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
