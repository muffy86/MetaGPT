#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def cmd_new(name: str) -> dict:
    root = Path("skills") / name
    root.mkdir(parents=True, exist_ok=True)
    (root / "SKILL.md").write_text("---\nname: {}\ndescription: \"\"\nwhen_to_use: \"\"\n---\n".format(name), encoding="utf-8")
    (root / "eval.yaml").write_text("name: eval\ncases: []\n", encoding="utf-8")
    (root / "redteam.py").write_text("CASES = []\n", encoding="utf-8")
    return {"created": str(root)}


def cmd_audit() -> dict:
    skills = [p.name for p in Path("skills").iterdir() if p.is_dir()]
    return {"skills": skills, "count": len(skills)}


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new")
    n.add_argument("name")
    sub.add_parser("audit")
    sub.add_parser("upgrade")
    sub.add_parser("prune")
    sub.add_parser("bundle")
    args = p.parse_args()
    if args.cmd == "new":
        out = cmd_new(args.name)
    elif args.cmd == "audit":
        out = cmd_audit()
    else:
        out = {"status": "ok", "cmd": args.cmd}
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
