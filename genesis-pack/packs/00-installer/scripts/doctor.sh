#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
python3 -m compileall packs >/dev/null
python3 packs/09-mobile/overrides/supervisor.py --profile desktop >/dev/null
python3 packs/09-mobile/overrides/supervisor.py --profile android-termux >/dev/null
python3 packs/03-retrieval/eval.py --quick >/dev/null
python3 packs/07-lab/replay.py runs/default/trace.jsonl --allow-missing >/dev/null
printf 'doctor: green\n'
