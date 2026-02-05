@echo off
rem Ollama Chat 快速啟動（Windows Batch）
rem 使用方式：chat.bat [額外參數]
rem
rem 覆蓋預設參數範例：
rem   chat.bat --model deepseek-r1:8b      # 覆蓋預設模型
rem   chat.bat --no-stream                 # 取消 streaming
rem   chat.bat --no-autosave               # 取消自動儲存
rem   chat.bat --system "新的提示詞"       # 覆蓋系統提示詞
rem   chat.bat --save chats/test.json      # 指定儲存路徑
rem   chat.bat --no-default-fallback       # 不使用預設 fallback 模型

cd /d "%~dp0"
uv run python ollama-chat.py ^
  --model qwen3-vl:8b ^
  --stream ^
  --system "總是以繁體中文回應訊息" ^
  --autosave ^
  %* ^
  --default-fallback deepseek-r1:8b ^
  --default-fallback llama3.1:8b
