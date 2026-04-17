#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../../.."
bash packs/06-interface/gx.sh ask "morning brief for today"
