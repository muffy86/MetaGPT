#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["enable", "disable"])
    parser.add_argument("name")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    src = root / "02-sensors" / "inputs" / f"{args.name}.yaml"
    dst_dir = root.parent / "data" / "sensors" / "enabled"
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name

    if args.action == "enable":
        if not src.exists():
            raise SystemExit(f"missing sensor: {src}")
        if dst.exists() or dst.is_symlink():
            dst.unlink()
        dst.symlink_to(src)
        print(f"enabled {args.name}")
    else:
        if dst.exists() or dst.is_symlink():
            dst.unlink()
        print(f"disabled {args.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
