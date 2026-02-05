@echo off
rem Ollama Chat 快速啟動（Windows Batch）
rem 使用方式：chat.bat [額外參數]
rem 範例：chat.bat --rag docs/ --temperature 0.5

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0chat.ps1" %*
