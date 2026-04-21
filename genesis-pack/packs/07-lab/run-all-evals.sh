#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
python3 packs/03-retrieval/eval.py --quick
python3 - <<'PY'
from pathlib import Path
import yaml
ok = True
for skill in Path('skills').iterdir():
    if not skill.is_dir():
        continue
    if not (skill / 'eval.yaml').exists() or not (skill / 'redteam.py').exists():
        ok = False
        print(f"missing eval/redteam: {skill.name}")
if not ok:
    raise SystemExit(2)
print('{"skills_eval": "pass"}')
PY
