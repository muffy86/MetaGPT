#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../../.."
python3 packs/07-lab/replay.py runs/default/trace.jsonl --allow-missing
