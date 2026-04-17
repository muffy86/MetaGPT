#!/usr/bin/env bash
set -euo pipefail
sudo apt-get update
sudo apt-get install -y python3 python3-venv jq curl
printf 'linux terminal bootstrap complete\n'
