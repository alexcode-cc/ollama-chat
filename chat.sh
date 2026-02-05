#!/bin/bash
# Ollama Chat 快速啟動（Linux / macOS）
# 使用方式：./chat.sh [額外參數]
# 範例：./chat.sh --rag docs/ --temperature 0.5

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec python3 "$SCRIPT_DIR/ollama-chat.py" \
  --model qwen3-vl:8b \
  --stream \
  --system "總是以繁體中文回應訊息" \
  --fallback deepseek-r1:8b \
  --fallback llama3.1:8b \
  --autosave \
  "$@"
