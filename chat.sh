#!/bin/bash
# Ollama Chat 快速啟動（Linux / macOS）
# 使用方式：./chat.sh [額外參數]
#
# 覆蓋預設參數範例：
#   ./chat.sh --model deepseek-r1:8b      # 覆蓋預設模型
#   ./chat.sh --no-stream                 # 取消 streaming
#   ./chat.sh --no-autosave               # 取消自動儲存
#   ./chat.sh --system "新的提示詞"       # 覆蓋系統提示詞
#   ./chat.sh --save chats/test.json      # 指定儲存路徑
#   ./chat.sh --no-default-fallback       # 不使用預設 fallback 模型

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

exec uv run python ollama-chat.py \
  --model qwen3-vl:8b \
  --stream \
  --system "總是以繁體中文回應訊息" \
  --autosave \
  "$@" \
  --default-fallback deepseek-r1:8b \
  --default-fallback llama3.1:8b
