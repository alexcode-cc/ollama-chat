# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案概述

這是一個單檔案 Python CLI 應用，用於與本地 Ollama LLM 進行互動式對話，支援 Streaming、Fallback 模型鏈和 RAG（檢索增強生成）功能。

## 常用指令

```bash
# 安裝依賴（使用 uv）
uv sync              # 基本安裝
uv sync --extra pdf  # 含 PDF 支援

# 快速啟動（推薦）
./chat.sh            # Linux / macOS
.\chat.ps1           # Windows PowerShell
chat.bat             # Windows CMD

# 基本執行
uv run python ollama-chat.py

# 指定模型與啟用 Streaming
uv run python ollama-chat.py --model llama3.1:8b --stream

# 使用 Fallback 模型鏈
uv run python ollama-chat.py --model llama3.1:8b --fallback mistral:7b --fallback gemma:7b

# 啟用 RAG
uv run python ollama-chat.py --rag docs/ --rag-k 4

# 完整配置範例
uv run python ollama-chat.py \
  --model llama3.1:8b \
  --fallback mistral:7b \
  --stream \
  --temperature 0.7 \
  --top-p 0.9 \
  --num-ctx 8192 \
  --system "你是一位資深顧問" \
  --rag docs/
```

## 系統需求

- Python 3.10+
- Ollama 在本機運行（localhost:11434）
- 至少一個聊天模型和一個 embedding 模型（預設：nomic-embed-text）

## 架構設計

### 模組結構

```
ollama-chat/
├── ollama-chat.py    # 主程式
├── pdf_loader.py     # PDF 文件讀取模組（可選）
├── pyproject.toml    # uv 依賴配置
├── chat.sh           # Linux/macOS 啟動腳本
├── chat.ps1          # PowerShell 啟動腳本
└── chat.bat          # Windows CMD 啟動腳本
```

### 主程式功能區塊

`ollama-chat.py` 包含 6 大功能區塊：

1. **Ollama 助手** - `get_installed_models()`, `build_options()` - 查詢模型與構建參數
2. **Embedding & RAG** - `embed_text()`, `cosine_similarity()`, `chunk_text()`, `load_documents()`, `build_rag_index()`, `retrieve_context()` - 文本向量化與檢索
3. **Chat API** - `chat_once()`, `chat_with_fallback()` - 對話請求與 fallback 機制
4. **History** - `save_history()`, `load_history()` - 對話紀錄存取
5. **Commands** - `cmd_*()` 系列函數 - 對話模式指令處理
6. **交互式循環** - `interactive_chat()` - 主對話迴圈與指令分派

### PDF Loader 模組

`pdf_loader.py` 提供 PDF 文件支援：

- `is_available()` - 檢查 pypdf 是否已安裝
- `load_pdf(path)` - 讀取單一 PDF 文件
- `load_pdfs_from_dir(directory)` - 從目錄讀取所有 PDF

主程式會自動偵測模組是否可用，若 pypdf 未安裝則降級為僅支援 Markdown/TXT。

### 關鍵設計模式

**Fallback 模型鏈**: 當主模型失敗時自動切換到備援模型，支援多層 fallback。

**Streaming 輸出**: Token 級實時輸出，使用 `resp.iter_lines()` 逐行解析 NDJSON。

**RAG 流程**:
- 文件 → 分塊（~500 字元） → Embedding（Ollama API） → 記憶體索引
- 查詢 → 向量化 → Cosine 相似度排序 → Top-K 注入 context

**訊息歷史**: 保留完整對話歷史（system/user/assistant 訊息列表）用於多輪上下文。

### 命令行參數

| 參數 | 說明 | 預設值 |
|------|------|--------|
| `--model` | 主要聊天模型 | `llama3.1:8b` |
| `--fallback` | 備援模型（可多個） | 無 |
| `--stream` | 啟用流式輸出 | False |
| `--system` | System prompt | 無 |
| `--rag` | RAG 文件目錄 | 無 |
| `--rag-k` | RAG 檢索結果數 | 4 |
| `--temperature` | 生成溫度 | 模型預設 |
| `--top-p` | 核心取樣比例 | 模型預設 |
| `--num-ctx` | Context window 大小 | 模型預設 |
| `--save` | 儲存對話紀錄路徑 | 無 |
| `--load` | 載入歷史對話路徑 | 無 |
| `--autosave` | 每輪自動儲存 | False |

### 對話模式指令

進入對話後可使用以下指令（以 `/` 開頭）：

| 指令 | 說明 |
|------|------|
| `/help`, `/h` | 顯示幫助訊息 |
| `/exit`, `/quit` | 退出程式 |
| `/clear` | 清除對話歷史（保留 system prompt） |
| `/history` | 顯示對話歷史摘要 |
| `/redo` | 重新生成最後一次回應 |
| `/save [path]` | 儲存對話（可選路徑，預設時間戳） |
| `/load <path>` | 載入對話歷史 |
| `/model` | 顯示當前模型鏈 |
| `/models` | 顯示所有可用模型 |
| `/status` | 顯示當前狀態 |

## 已知限制

- RAG 索引為純記憶體（重啟丟失）
- Chunk size 為字元估算（非精準 token 計算）

## Git Commit 規範

遵循 AngularJS Git Commit Message Conventions，所有提交訊息使用**繁體中文**。

### 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type 類型

| Type | 說明 |
|------|------|
| `feat` | 新功能 |
| `fix` | 修復 bug |
| `docs` | 文檔變更 |
| `style` | 格式調整（不影響程式碼運行） |
| `refactor` | 重構（不新增功能也不修復 bug） |
| `perf` | 性能優化 |
| `test` | 新增或修改測試 |
| `chore` | 建置過程或輔助工具的變動 |

### 範例

```
feat(rag): 新增 PDF 文件支援

使用 pypdf 庫解析 PDF 文件，支援多頁文件的文字提取與分塊處理。

Closes #12
```

```
fix(chat): 修正 streaming 模式下的編碼問題
```

```
docs: 更新 README 安裝說明
```
