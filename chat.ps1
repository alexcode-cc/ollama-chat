# Ollama Chat 快速啟動（PowerShell / Windows / macOS / Linux）
# 使用方式：.\chat.ps1 [額外參數]
#
# 覆蓋預設參數範例：
#   .\chat.ps1 --model deepseek-r1:8b      # 覆蓋預設模型
#   .\chat.ps1 --no-stream                 # 取消 streaming
#   .\chat.ps1 --no-autosave               # 取消自動儲存
#   .\chat.ps1 --system "新的提示詞"       # 覆蓋系統提示詞
#   .\chat.ps1 --save chats/test.json      # 指定儲存路徑
#   .\chat.ps1 --no-default-fallback       # 不使用預設 fallback 模型

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $ScriptDir

try {
    uv run python ollama-chat.py `
      --model qwen3-vl:8b `
      --stream `
      --system "總是以繁體中文回應訊息" `
      --autosave `
      @args `
      --default-fallback deepseek-r1:8b `
      --default-fallback llama3.1:8b
} finally {
    Pop-Location
}
