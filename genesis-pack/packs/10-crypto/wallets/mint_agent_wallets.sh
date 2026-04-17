#!/usr/bin/env bash
set -euo pipefail
mkdir -p data/crypto
cat > data/crypto/wallets.json <<JSON
[{"chain":"base","address":"0x0000000000000000000000000000000000000000"}]
JSON
printf 'wallets minted\n'
