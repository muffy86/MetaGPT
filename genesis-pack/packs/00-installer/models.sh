#!/usr/bin/env bash
PROFILE=$(cat .profile)
# Desktop/DeX: full models
if [[ "$PROFILE" =~ ^(macos-arm|linux-x64|android-linux-terminal)$ ]]; then
  ollama pull qwen3-coder:30b
  ollama pull qwen3:14b
  ollama pull gemma3:12b
  ollama pull bge-m3
  ollama pull moondream:2b
  # Reranker (not on Ollama; via transformers)
  uv run python -c "from sentence_transformers import CrossEncoder; CrossEncoder('BAAI/bge-reranker-v2.5-gemma2-lightweight')"
else
  # Termux / mobile: trimmed
  ollama pull qwen3-coder:7b
  ollama pull gemma3:4b
  ollama pull bge-m3
fi
# whisper.cpp model
mkdir -p models && cd models
[[ -f ggml-large-v3-turbo-q5_0.bin ]] || \
  curl -L -o ggml-large-v3-turbo-q5_0.bin https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q5_0.bin
