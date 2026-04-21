#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$ROOT_DIR/scripts/policy_check.py" \
  '{"tool":"invoke","args":{"tool_name":"read_file","path":"packs/GENESIS-PACK.md"}}' \
  '{"data_classification":"internal","destructive":false}' >/dev/null
printf "policy check: ok\n"
