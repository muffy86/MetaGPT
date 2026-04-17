#!/usr/bin/env python3
"""Resolve 1Password references without printing secret values."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve op:// references safely.")
    parser.add_argument("reference", help="1Password secret reference, e.g. op://vault/item/field")
    args = parser.parse_args()

    proc = subprocess.run(
        ["op", "read", args.reference],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        print(json.dumps({"ok": False, "reference": args.reference, "error": proc.stderr.strip()}))
        return proc.returncode

    # Intentionally avoid printing the raw secret value.
    print(json.dumps({"ok": True, "reference": args.reference, "resolved": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
