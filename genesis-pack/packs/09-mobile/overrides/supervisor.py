#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json


PROFILES = {
    "desktop": {"status": "green", "compose": True, "model": "claude-sonnet-4-5"},
    "android-termux": {"status": "green", "compose": False, "model": "qwen3-coder:7b"},
}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--profile", default="desktop")
    args = p.parse_args()
    print(json.dumps(PROFILES.get(args.profile, {"status": "unknown"})))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
