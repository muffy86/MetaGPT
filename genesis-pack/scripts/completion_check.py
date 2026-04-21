#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import subprocess
import sys


@dataclass
class CheckResult:
    name: str
    cmd: str
    ok: bool
    code: int
    stdout: str
    stderr: str


def run_check(name: str, cmd: str, cwd: Path) -> CheckResult:
    proc = subprocess.run(cmd, cwd=str(cwd), shell=True, text=True, capture_output=True)
    return CheckResult(
        name=name,
        cmd=cmd,
        ok=proc.returncode == 0,
        code=proc.returncode,
        stdout=(proc.stdout or "").strip(),
        stderr=(proc.stderr or "").strip(),
    )


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    checks = [
        ("compile", "python3 -m compileall packs"),
        ("pack-install", "./packs/00-installer/scripts/pack-install.sh"),
        ("doctor", "./packs/00-installer/scripts/doctor.sh"),
        ("skill-lint", "python3 packs/08-forge/skill_lint.py skills"),
        ("retrieval-eval", "python3 packs/03-retrieval/eval.py --quick"),
        ("twin-calibrate", "python3 packs/04-twin/calibrate.py"),
        ("strategy-run", "python3 packs/10-crypto/defai/run_strategy.py"),
        ("replay", "python3 packs/07-lab/replay.py runs/default/trace.jsonl --allow-missing"),
    ]

    results = [run_check(name, cmd, root) for name, cmd in checks]
    passed = sum(1 for r in results if r.ok)
    total = len(results)

    report = {
        "ts": datetime.now(tz=timezone.utc).isoformat(),
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "checks": [
            {
                "name": r.name,
                "ok": r.ok,
                "code": r.code,
                "cmd": r.cmd,
                "stdout": r.stdout[-1500:],
                "stderr": r.stderr[-1500:],
            }
            for r in results
        ],
    }

    out_dir = root / "packs" / "00-installer" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "completion-check-latest.json"
    out_file.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps({"report": str(out_file), "passed": passed, "total": total}))
    return 0 if passed == total else 2


if __name__ == "__main__":
    raise SystemExit(main())
