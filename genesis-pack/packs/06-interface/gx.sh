#!/usr/bin/env bash
set -euo pipefail
cmd="${1:-help}"
shift || true
case "$cmd" in
  ask)
    python3 packs/06-interface/gx_ask.py "$@"
    ;;
  twin)
    python3 packs/04-twin/cli.py "$@"
    ;;
  *)
    echo "usage: gx ask <query> | gx twin ..."
    ;;
esac
