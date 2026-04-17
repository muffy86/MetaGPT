#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
mkdir -p data runs vault data/exocortex data/sensors/{state,enabled} data/twin
python3 packs/01-exocortex/init.py
bash packs/02-sensors/scripts/enable-defaults.sh
printf 'pack-install complete\n'
