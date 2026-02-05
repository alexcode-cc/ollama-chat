# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案概述

這是一個單檔案 Python CLI 應用，用於與本地 Ollama LLM 進行互動式對話，支援 Streaming、Fallback 模型鏈和 RAG（檢索增強生成）功能。

## 常用指令

```bash
# 安裝依賴（使用 uv）
uv sync                 # 基本安裝
uv sync --extra pdf     # 含 PDF 支援
uv sync --extra windows # Windows 行編輯支援
uv sync --extra all     # 完整安裝

# 快速啟動（推薦）
./chat.sh            # Linux / macOS
.\chat.ps1           # Windows PowerShell

# 基本執行
uv run python ollama-chat.py

# 常用組合
uv run python ollama-chat.py --model llama3.1:8b --stream --autosave
uv run python ollama-chat.py --rag docs/ --rag-k 4

# 覆蓋啟動腳本預設參數
.\chat.ps1 --model deepseek-r1:8b      # 覆蓋預設模型
.\chat.ps1 --no-stream                 # 取消 streaming
.\chat.ps1 --no-autosave               # 取消自動儲存
.\chat.ps1 --system "新的提示詞"       # 覆蓋系統提示詞
.\chat.ps1 --save chats/test.json      # 指定儲存路徑
.\chat.ps1 --no-default-fallback       # 不使用預設 fallback 模型
```

本專案無測試套件。執行 `--help` 查看完整參數，進入對話後輸入 `/help` 查看指令。

## 系統需求

- Python 3.10+
- Ollama 在本機運行（localhost:11434）
- 聊天模型 + embedding 模型（預設：nomic-embed-text）

## 架構設計

### 核心模組

- **ollama-chat.py** - 主程式（約 600 行），包含所有核心邏輯
- **pdf_loader.py** - PDF 文件讀取模組（可選，自動偵測 pypdf 可用性）

### 主程式功能區塊（ollama-chat.py）

程式碼以註解分隔為清晰區塊：

1. **Ollama helpers** (~L49) - `get_installed_models()`, `build_options()`
2. **Embedding & RAG** (~L69) - 向量化、分塊、索引建立、檢索
3. **Spinner** (~L135) - 等待動畫類別
4. **Chat** (~L166) - `chat_once()`, `chat_with_fallback()`
5. **History** (~L225) - 對話記錄存取與 JSON/CSV 轉換
6. **Commands** (~L259) - `cmd_*()` 系列函數，處理 `/` 開頭指令
7. **Interactive** (~L407) - `interactive_chat()` 主迴圈

### 關鍵設計模式

**Fallback 模型鏈**: 主模型失敗時自動切換備援模型，由 `chat_with_fallback()` 實現。

**Streaming 輸出**: 使用 `resp.iter_lines()` 逐行解析 NDJSON，Token 級實時輸出。

**RAG 流程**: 文件 → 分塊（~500 字元） → Embedding → 記憶體索引 → Cosine 相似度檢索 → Top-K 注入 context。

**可選依賴降級**: pdf_loader 和 readline 皆為可選，程式自動偵測並降級。

**參數覆蓋機制**: 啟動腳本設定預設參數，用戶參數可覆蓋：
- 單值參數（--model, --system, --save）：後者覆蓋前者（argparse 預設行為）
- 布林參數（--stream, --autosave）：使用 `BooleanOptionalAction`，支援 `--no-*` 取消
- Fallback 模型：腳本用 `--default-fallback`，用戶可用 `--no-default-fallback` 完全排除

## 已知限制

- RAG 索引為純記憶體（重啟丟失）
- Chunk size 為字元估算（非精準 token 計算）

## Git Commit 規範

遵循 AngularJS Commit Conventions，所有提交訊息使用**繁體中文**。

格式：`<type>(<scope>): <subject>`

| Type | 說明 |
|------|------|
| `feat` | 新功能 |
| `fix` | 修復 bug |
| `docs` | 文檔變更 |
| `style` | 格式調整 |
| `refactor` | 重構 |
| `perf` | 性能優化 |
| `test` | 測試相關 |
| `chore` | 建置/工具變動 |

範例：`feat(rag): 新增 PDF 文件支援`
