#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

NAME_RE = re.compile(r"^[a-z0-9-]{1,64}$")


def lint_skill(path: Path) -> list[str]:
    issues: list[str] = []
    md = path / "SKILL.md"
    if not md.exists():
        issues.append(f"{path.name}: missing SKILL.md")
        return issues
    text = md.read_text(encoding="utf-8")
    if "## Gotchas" not in text:
        issues.append(f"{path.name}: missing ## Gotchas")
    if "DO NOT use for:" not in text:
        issues.append(f"{path.name}: missing DO NOT use for")
    if not (path / "eval.yaml").exists():
        issues.append(f"{path.name}: missing eval.yaml")
    if not (path / "redteam.py").exists():
        issues.append(f"{path.name}: missing redteam.py")
    m = re.search(r"name:\s*([a-z0-9-]+)", text)
    if m and not NAME_RE.match(m.group(1)):
        issues.append(f"{path.name}: invalid name")
    return issues


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("skills_dir")
    args = p.parse_args()
    root = Path(args.skills_dir)
    issues: list[str] = []
    for skill in sorted([x for x in root.iterdir() if x.is_dir()]):
        issues.extend(lint_skill(skill))
    if issues:
        for i in issues:
            print(i)
        return 2
    print("skill lint: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
