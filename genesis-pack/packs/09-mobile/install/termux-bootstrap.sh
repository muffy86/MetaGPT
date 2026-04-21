#!/usr/bin/env bash
set -euo pipefail
pkg update -y
pkg install -y git python nodejs-lts openssh
printf 'termux bootstrap complete\n'
