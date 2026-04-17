#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if command -v promptfoo >/dev/null 2>&1; then
  promptfoo eval -c "$ROOT_DIR/assets/promptfoo.yaml"
else
  echo "promptfoo not installed; skipping promptfoo eval"
fi

python3 "$ROOT_DIR/inspect/injection_suite.py"
