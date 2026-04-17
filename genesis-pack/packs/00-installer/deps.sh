#!/usr/bin/env bash
set -euo pipefail
PROFILE=$(cat .profile)

case "$PROFILE" in
  macos-arm)
    command -v brew >/dev/null || /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    brew install age uv just gh gitleaks jq yq ripgrep fd duckdb ollama 1password-cli opa deno bun
    brew install --cask docker rectangle
    ;;
  linux-x64|linux-arm)
    sudo apt-get update && sudo apt-get install -y age jq yq ripgrep fd-find gitleaks python3.12 python3.12-venv pipx docker.io docker-compose-plugin
    curl -LsSf https://astral.sh/uv/install.sh | sh
    curl -fsSL https://just.systems/install.sh | bash -s -- --to /usr/local/bin
    curl -fsSL https://github.com/cli/cli/releases/latest/download/gh_linux_amd64.tar.gz | tar xz && sudo mv gh_*/bin/gh /usr/local/bin/
    curl -fsSL https://ollama.com/install.sh | sh
    op_url="https://cache.agilebits.com/dist/1P/op2/pkg/v2.30.0/op_linux_amd64_v2.30.0.zip"; curl -sS "$op_url" -o op.zip && unzip op.zip op -d /usr/local/bin/
    ;;
  android-termux)
    pkg update -y && pkg upgrade -y
    pkg install -y git curl wget openssh openssl clang make cmake pkg-config python python-pip rust golang nodejs-lts tmux jq ripgrep fd sqlite duckdb ffmpeg tesseract termux-api proot proot-distro android-tools
    curl -LsSf https://astral.sh/uv/install.sh | sh
    curl -fsSL https://bun.sh/install | bash
    curl -fsSL https://ollama.com/install.sh | sh
    # op CLI ARM64
    curl -sS https://cache.agilebits.com/dist/1P/op2/pkg/v2.30.0/op_linux_arm64_v2.30.0.zip -o /tmp/op.zip
    unzip /tmp/op.zip op -d $PREFIX/bin/
    # justfile runner
    cargo install just
    ;;
  android-linux-terminal)
    sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin build-essential python3.12 python3.12-venv pipx nodejs npm age gitleaks jq yq ripgrep fd-find
    curl -LsSf https://astral.sh/uv/install.sh | sh
    curl -fsSL https://ollama.com/install.sh | sh
    ;;
esac
echo "deps installed for $PROFILE"
