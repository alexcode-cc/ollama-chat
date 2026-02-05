# 變更歷史

本文件記錄 Ollama Chat CLI 的版本更新歷史。

格式基於 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/)，
版本號遵循 [Semantic Versioning](https://semver.org/lang/zh-TW/)。

---

## [1.0.0] - 2026-02-05

### 新增功能

#### 核心功能
- **多輪對話**：使用 Ollama `/api/chat` 實現完整的上下文記憶
- **Streaming 輸出**：Token 級實時輸出，提升使用者體驗
- **Fallback 模型鏈**：主模型失敗時自動切換備援模型，確保高可用性
- **RAG 檢索增強生成**：支援文件向量化與語義檢索
  - 支援 Markdown (.md)、純文字 (.txt)、PDF (.pdf) 格式
  - 使用 Ollama Embedding API 進行向量化
  - Cosine 相似度排序取 Top-K

#### 對話紀錄
- `--save`：指定儲存對話紀錄路徑
- `--load`：載入歷史對話
- `--autosave`：每輪對話自動儲存（預設路徑 `chats/YYYY-MM-DD-HH-mm-ss.json`）

#### 對話模式指令
- `/help`, `/h`：顯示幫助訊息
- `/exit`, `/quit`：退出程式
- `/clear`：清除對話歷史（保留 system prompt）
- `/history`：顯示對話歷史摘要
- `/redo`：重新生成最後一次回應
- `/save [path]`：手動儲存對話
- `/load <path>`：載入對話歷史
- `/model`：顯示當前模型鏈
- `/models`：顯示所有可用模型
- `/status`：顯示當前狀態

#### 命令行參數
- `--model`：指定主要聊天模型（預設 `llama3.1:8b`）
- `--fallback`：指定備援模型（可多次使用）
- `--stream`：啟用串流輸出
- `--system`：設定 system prompt
- `--rag`：指定 RAG 文件目錄
- `--rag-k`：RAG 檢索結果數量（預設 4）
- `--temperature`：生成溫度
- `--top-p`：核心取樣比例
- `--num-ctx`：Context window 大小

#### 跨平台支援
- `chat.sh`：Linux / macOS 快速啟動腳本
- `chat.ps1`：PowerShell 快速啟動腳本（跨平台）
- `chat.bat`：Windows Batch 快速啟動腳本

#### 模組化設計
- `pdf_loader.py`：獨立的 PDF 讀取模組
  - 自動偵測 pypdf 是否安裝
  - 優雅降級：未安裝時不影響核心功能

### 技術規格

- **Python 版本**：3.10+
- **必要依賴**：requests
- **可選依賴**：pypdf（PDF 支援）
- **Ollama 版本**：需本機運行 Ollama 服務（localhost:11434）

### 文件

- `README.md`：專案說明與使用指南
- `CLAUDE.md`：Claude Code 開發指南
- `docs/implementation.md`：詳細實作文檔
- `LICENSE.txt`：MIT 授權

---

## 版本規劃

### [1.1.0] - 計劃中
- SQLite / FAISS 向量索引持久化
- 更多文件格式支援（DOCX、HTML）

### [2.0.0] - 長期規劃
- FastAPI HTTP 服務
- Web UI 介面
- 多使用者支援

---

[1.0.0]: https://github.com/alex/ollama-chat/releases/tag/v1.0.0
