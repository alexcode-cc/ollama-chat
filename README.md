# Ollama Chat CLI with RAG

一個**本地優先（Local-first）**、**工程級穩定**的 Ollama CLI 工具，支援：

- 🧠 多輪對話（Chat API）
- 🔧 可調教生成參數（temperature / top_p / num_ctx）
- 🛡 自動 fallback 模型（高可用）
- 💾 聊天紀錄載入 / 存檔（JSON）
- 📚 RAG（資料夾文件檢索，Markdown / TXT / PDF）
- ⚡ Streaming 即時輸出
- ⌨️ 完整行編輯功能（方向鍵、歷史記錄）

> 適合：**資安研究、內部知識助理、專案顧問、離線 LLM 使用場景**

---

## 功能總覽

| 功能 | 說明 |
|----|----|
| 多輪對話 | 使用 Ollama `/api/chat`，模型能記住上下文 |
| 生成參數 | `temperature` / `top_p` / `num_ctx` |
| Fallback | 主模型失敗自動切換備援模型 |
| 歷史紀錄 | JSON 載入 / 存檔 / autosave |
| RAG | 讀取資料夾文件並做 embedding 檢索 |
| Streaming | Token 級即時輸出 |
| 等待動畫 | 送出對話後顯示旋轉動畫 |
| 行編輯 | 方向鍵、歷史瀏覽、快捷鍵 |

---

## 系統需求

- Python **3.10+**
- 本機已安裝並啟動 **Ollama**
- Ollama 內至少有：
  - 一個聊天模型（如 `llama3.1:8b`）
  - 一個 embedding 模型（預設：`nomic-embed-text`）

```bash
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

---

## 安裝

本專案使用 [uv](https://docs.astral.sh/uv/) 管理依賴。

```bash
# 安裝 uv（如尚未安裝）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 基本安裝
uv sync

# 含 PDF 支援
uv sync --extra pdf

# Windows 行編輯支援
uv sync --extra windows

# 完整安裝
uv sync --extra all
```

---

## 基本使用

### 快速啟動（推薦）

```bash
# Linux / macOS
./chat.sh

# Windows PowerShell
.\chat.ps1

# Windows CMD
chat.bat
```

快速啟動腳本包含預設參數：模型鏈、Streaming、繁體中文、Autosave。

### 手動執行

```bash
# 啟動聊天
uv run python ollama-chat.py

# 指定模型
uv run python ollama-chat.py --model llama3.1:8b

# 即時輸出（Streaming）
uv run python ollama-chat.py --stream
```

---

## 生成參數調教

```bash
uv run python ollama-chat.py \
  --temperature 0.7 \
  --top-p 0.9 \
  --num-ctx 8192
```

| 參數 | 說明 |
|----|----|
| temperature | 創造力 / 發散度 |
| top_p | 核心取樣比例 |
| num_ctx | Context window 大小 |

---

## System Prompt（角色設定）

```bash
uv run python ollama-chat.py \
  --system "你是一位資深資安顧問，回答請務實且附建議"
```

---

## Fallback 模型（高可用）

當主模型失敗（OOM / timeout / 500），會自動切換。

```bash
uv run python ollama-chat.py \
  --model llama3.1:8b \
  --fallback mistral:7b \
  --fallback qwen2.5:7b
```

執行時會顯示：

```
🔄 使用模型：llama3.1:8b
⚠️ 模型失敗，自動切換…
🔄 使用模型：mistral:7b
```

---

## 聊天紀錄（History）

### 載入舊對話

```bash
uv run python ollama-chat.py --load chats/project.json
```

### 存檔

```bash
uv run python ollama-chat.py --save chats/today.json
```

### Autosave（每一輪即時寫檔）

```bash
# 使用指定路徑
uv run python ollama-chat.py --save chats/long_session.json --autosave

# 或使用預設時間戳路徑（chats/YYYY-MM-DD-HH-mm-ss.json）
uv run python ollama-chat.py --autosave
```

### JSON 格式

```json
{
  "meta": {
    "model_chain": ["llama3.1:8b", "mistral:7b"],
    "options": {"temperature": 0.7},
    "created_at": "2026-02-05T12:00:00"
  },
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

---

## RAG（Retrieval-Augmented Generation）

### 資料夾結構

```
docs/
 ├─ spec.md
 ├─ design.md
 └─ notes.txt
```

### 啟用 RAG

```bash
uv run python ollama-chat.py \
  --rag docs/ \
  --rag-k 4 \
  --system "請根據文件內容回答"
```

### RAG 行為說明

- 自動讀取 `.md` / `.txt` / `.pdf`
- 切 chunk（約 500 字）
- 使用 `nomic-embed-text` 做 embedding
- cosine similarity 取 Top-K
- 相關內容會注入 system context

> PDF 支援需安裝 `pypdf`，程式會自動偵測並啟用

---

## 常見使用場景

- 🛡 內部資安文件 / SOP 查詢
- 📘 專案規格 / 設計文件 QA
- 🧠 私有知識庫助理（完全離線）
- 🔍 稽核 / 研究輔助工具

---

## 已知限制

- RAG index 目前為記憶體內（重啟需重建）
- Chunk size 為字元近似（非 token 精準）

---

## Roadmap（形態進化）

- ✅ PDF loader（pypdf）- 已完成
- 🗄 SQLite / FAISS 向量索引
- 🌐 FastAPI / Web UI / PWA
- 👥 多使用者 / API Key
- 📦 pip install + shell autocomplete

---

## 授權

MIT License

---

> 這不是玩具 CLI，而是一個**可進化成產品形態的本地 LLM 核心**。

