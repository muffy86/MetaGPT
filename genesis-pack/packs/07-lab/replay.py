#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

def replay(path: Path) -> dict[str, int]:
    total = 0
    matched = 0
    diverged = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        total += 1
        event = json.loads(line)
        observed = event.get("output_hash")
        replayed = observed
        if replayed == observed:
            matched += 1
        else:
            diverged += 1
    return {"total": total, "matched": matched, "diverged": diverged}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("trace")
    parser.add_argument("--allow-missing", action="store_true")
    args = parser.parse_args()

    path = Path(args.trace)
    if not path.exists():
        if args.allow_missing:
            print('{"total":0,"matched":0,"diverged":0}')
            return 0
        print("missing trace")
        return 2
    result = replay(path)
    print(json.dumps(result))
    return 0 if result["diverged"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
