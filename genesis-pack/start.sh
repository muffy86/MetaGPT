#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if command -v uv >/dev/null 2>&1; then
  uv run uvicorn packs.06-interface.web.app:app --host 0.0.0.0 --port 7777 --reload
else
  python3 -m uvicorn packs.06-interface.web.app:app --host 0.0.0.0 --port 7777 --reload
fi
