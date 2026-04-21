#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${GENESIS_ANDROID_DATA_DIR:-$ROOT_DIR/../../data/android}"

mkdir -p "$DATA_DIR"/{inbox,sms,clipboard,state}
printf "android-edge bootstrap complete: %s\n" "$DATA_DIR"
