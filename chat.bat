@echo off
rem Ollama Chat 快速啟動（Windows Batch）
rem 使用方式：chat.bat [額外參數]
rem 範例：chat.bat --rag docs/ --temperature 0.5

cd /d "%~dp0"
uv run python ollama-chat.py ^
  --model qwen3-vl:8b ^
  --stream ^
  --system "總是以繁體中文回應訊息" ^
  --fallback deepseek-r1:8b ^
  --fallback llama3.1:8b ^
  --autosave ^
  %*
