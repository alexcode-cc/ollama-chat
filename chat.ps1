# Ollama Chat 快速啟動（PowerShell / Windows / macOS / Linux）
# 使用方式：.\chat.ps1 [額外參數]
# 範例：.\chat.ps1 --rag docs/ --temperature 0.5

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

& python "$ScriptDir\ollama-chat.py" `
  --model qwen3-vl:8b `
  --stream `
  --system "總是以繁體中文回應訊息" `
  --fallback deepseek-r1:8b `
  --fallback llama3.1:8b `
  --autosave `
  @args
