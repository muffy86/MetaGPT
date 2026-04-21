#!/usr/bin/env python3
"""Tiny OPA policy gate wrapper for destructive operations."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

POLICY = Path(__file__).resolve().parents[1] / "assets" / "policies.rego"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: policy_check.py '<json-input>'", file=sys.stderr)
        return 2
    try:
        payload = json.loads(sys.argv[1])
    except json.JSONDecodeError as exc:
        print(f"invalid json payload: {exc}", file=sys.stderr)
        return 2

    if not POLICY.exists():
        print(f"missing policy bundle: {POLICY}", file=sys.stderr)
        return 2

    cmd = [
        "opa",
        "eval",
        "-d",
        str(POLICY),
        "-I",
        "data.genesis.authz.allow",
    ]
    proc = subprocess.run(cmd, input=json.dumps(payload), text=True, capture_output=True)
    if proc.returncode != 0:
        print(proc.stderr.strip() or "opa eval failed", file=sys.stderr)
        return 1
    raw = proc.stdout.strip()
    allowed = raw.endswith("true")
    if allowed:
        print("allow")
        return 0
    print("deny")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
