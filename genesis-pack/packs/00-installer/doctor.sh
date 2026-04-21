#!/usr/bin/env bash
OK=0; FAIL=0
check() { printf "  %-38s" "$1"; if eval "$2" >/dev/null 2>&1; then echo "✓"; OK=$((OK+1)); else echo "✗"; FAIL=$((FAIL+1)); fi; }

echo "─── genesis doctor ───"
check "duckdb ledger"       "duckdb data/ledger.duckdb -c 'SELECT 1'"
check "iceberg extension"   "duckdb data/ledger.duckdb -c 'SELECT * FROM duckdb_extensions() WHERE extension_name=\"iceberg\" AND loaded=true'"
check "lancedb"             "python -c 'import lancedb; lancedb.connect(\"data/exocortex/embeddings.lance\").table_names()'"
check "kuzu graph"          "python -c 'import kuzu; kuzu.Database(\"data/exocortex/graph.kuzu\")'"
check "ollama running"      "curl -s http://localhost:11434/api/tags | grep -q models"
check "model qwen3-coder"   "curl -s http://localhost:11434/api/tags | grep -q qwen3-coder"
check "model bge-m3"        "curl -s http://localhost:11434/api/tags | grep -q bge-m3"
check "op cli"              "op account list"
check "age"                 "command -v age"
check "tailscale"           "tailscale status"
check "opa policy compiles" "opa check assets/policies.rego"
check "gitleaks"            "command -v gitleaks"
check "litellm proxy"       "curl -s http://localhost:4000/health"
check "phoenix ui"          "curl -s http://localhost:6006 -o /dev/null"
check "inngest dev"         "curl -s http://localhost:8288/health"
check "redpanda connect"    "curl -s http://localhost:8880/ping"
check "playwright mcp"      "which npx && npx -y @playwright/mcp@latest --help"
echo "─── $OK ok · $FAIL fail ───"
[[ $FAIL -eq 0 ]] || exit 1
