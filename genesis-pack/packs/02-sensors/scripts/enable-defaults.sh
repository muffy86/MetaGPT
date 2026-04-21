#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INPUT_DIR="$ROOT_DIR/02-sensors/inputs"
ENABLED_DIR="${GENESIS_SENSORS_ENABLED_DIR:-$ROOT_DIR/../data/sensors/enabled}"

mkdir -p "$ENABLED_DIR"

defaults=(
  "screenpipe.yaml"
  "clipboard.yaml"
  "browser-history.yaml"
  "cli-history.yaml"
  "obsidian.yaml"
)

for file in "${defaults[@]}"; do
  if [[ -f "$INPUT_DIR/$file" ]]; then
    ln -sf "$INPUT_DIR/$file" "$ENABLED_DIR/$file"
    printf "enabled sensor: %s\n" "$file"
  else
    printf "missing sensor definition: %s\n" "$file" >&2
  fi
done

printf "sensor defaults enabled in %s\n" "$ENABLED_DIR"
