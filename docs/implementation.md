# Ollama Chat CLI 實作文檔

本文檔詳細記錄了 Ollama Chat CLI 專案的完整實作過程，包含架構設計、各模組實作細節、重構歷程與設計決策。

---

## 目錄

1. [專案概述](#專案概述)
2. [開發歷程](#開發歷程)
3. [架構設計](#架構設計)
4. [模組實作詳解](#模組實作詳解)
5. [指令系統實作](#指令系統實作)
6. [設計決策與考量](#設計決策與考量)
7. [未來展望](#未來展望)

---

## 專案概述

### 專案目標

建立一個**本地優先（Local-first）**的 CLI 工具，用於與本機運行的 Ollama LLM 進行互動式對話，具備以下核心功能：

- 多輪對話（Chat API）
- 串流輸出（Streaming）
- 高可用 Fallback 模型鏈
- RAG（檢索增強生成）
- 對話歷史紀錄管理

### 技術棧

| 項目 | 技術選型 |
|------|---------|
| 語言 | Python 3.10+ |
| HTTP 客戶端 | requests |
| PDF 解析 | pypdf（可選） |
| 向量化 | Ollama Embedding API |
| 資料格式 | JSON |

### 檔案結構

```
ollama-chat/
├── ollama-chat.py    # 主程式（~430 行）
├── pdf_loader.py     # PDF 讀取模組（~74 行）
├── chat.sh           # Linux/macOS 啟動腳本
├── chat.ps1          # PowerShell 啟動腳本
├── chat.bat          # Windows Batch 啟動腳本
├── CLAUDE.md         # Claude Code 開發指南
├── README.md         # 專案說明文檔
├── LICENSE.txt       # MIT 授權
└── docs/
    └── implementation.md  # 本文檔
```

---

## 開發歷程

以下按照 Git 提交順序記錄專案的演進過程：

### Phase 1：基礎建設

#### 1.1 初始化專案配置
```
391b299 chore: 新增 .gitignore 配置
```

建立 Python 專案的 `.gitignore`，涵蓋：
- Python 快取與編譯檔案（`__pycache__/`, `*.pyc`）
- 虛擬環境目錄（`.venv/`, `env/`）
- IDE 設定檔（`.idea/`, `.vscode/`）
- 測試覆蓋率報告（`.coverage`, `htmlcov/`）
- 本地配置檔案（`.env.local`）

#### 1.2 核心功能實作
```
3cd3636 feat(chat): 實作 Ollama 互動式聊天客戶端
```

首次提交的核心功能：
- Ollama API 整合（`/api/tags`, `/api/chat`, `/api/embeddings`）
- 多輪對話上下文管理
- Streaming 輸出支援
- Fallback 模型鏈機制
- RAG 檢索增強生成
- 命令行參數解析

### Phase 2：文檔完善

#### 2.1 專案文檔
```
db13779 docs: 新增專案 README 文檔
0fc468c docs: 新增 CLAUDE.md 開發指南
74eb119 docs: add MIT License
```

建立完整的專案文檔體系：
- README.md：使用者導向的說明文檔
- CLAUDE.md：開發者導向的技術指南
- LICENSE.txt：MIT 開源授權

### Phase 3：PDF 支援

#### 3.1 模組化 PDF Loader
```
79b8796 feat(rag): 新增 PDF 文件支援
30f6cce docs: 更新文檔以反映 PDF 支援功能
```

關鍵設計決策：
- **模組化**：將 PDF 功能獨立為 `pdf_loader.py`
- **優雅降級**：pypdf 未安裝時自動降級，不影響核心功能
- **自動偵測**：主程式透過 `try-except` 偵測模組可用性

```python
try:
    import pdf_loader
    PDF_SUPPORT = pdf_loader.is_available()
except ImportError:
    PDF_SUPPORT = False
```

### Phase 4：對話紀錄功能

#### 4.1 History 模組
```
cf6304f feat(chat): 實作 --autosave 時間戳預設儲存
```

實作對話紀錄的儲存與載入：
- `--save`：指定儲存路徑
- `--load`：載入歷史對話
- `--autosave`：每輪對話自動儲存

**時間戳預設路徑**：當 `--autosave` 啟用但未指定 `--save` 時，自動生成：
```
chats/YYYY-MM-DD-HH-mm-ss.json
```

#### 4.2 跨平台啟動腳本
```
37a453e chore: 新增跨平台快速執行指令稿
```

建立三個啟動腳本，統一預設參數：
- `chat.sh`：Bash（Linux/macOS）
- `chat.ps1`：PowerShell（跨平台）
- `chat.bat`：Windows Batch（呼叫 chat.ps1）

### Phase 5：指令系統

#### 5.1 對話模式指令
```
33698b5 feat(chat): 新增對話模式指令系統
9b85bad docs: 更新文檔，新增對話模式指令說明
```

重構對話迴圈，加入完整的指令系統：
- 將退出指令從 `exit`/`quit` 改為 `/exit`/`/quit`
- 新增 10 個對話模式指令
- 加入 `Ctrl+C` 中斷處理

---

## 架構設計

### 整體架構圖

```
┌─────────────────────────────────────────────────────────────┐
│                        main()                                │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                  argparse 參數解析                       ││
│  │  --model, --fallback, --stream, --system, --rag, etc.   ││
│  └─────────────────────────────────────────────────────────┘│
│                            │                                 │
│                            ▼                                 │
│  ┌─────────────────────────────────────────────────────────┐│
│  │               interactive_chat(args)                     ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  ││
│  │  │  RAG Index  │  │   History   │  │  Command Parser │  ││
│  │  │  (optional) │  │  Load/Save  │  │  /help, /redo.. │  ││
│  │  └─────────────┘  └─────────────┘  └─────────────────┘  ││
│  │                            │                             ││
│  │                            ▼                             ││
│  │  ┌─────────────────────────────────────────────────────┐││
│  │  │              chat_with_fallback()                   │││
│  │  │  model_chain: [primary] → [fallback1] → [fallback2] │││
│  │  └─────────────────────────────────────────────────────┘││
│  │                            │                             ││
│  │                            ▼                             ││
│  │  ┌─────────────────────────────────────────────────────┐││
│  │  │                  chat_once()                        │││
│  │  │  ┌─────────────┐              ┌─────────────────┐   │││
│  │  │  │  Streaming  │      or      │  Non-Streaming  │   │││
│  │  │  │ iter_lines  │              │   json resp     │   │││
│  │  │  └─────────────┘              └─────────────────┘   │││
│  │  └─────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Ollama Server                             │
│                  localhost:11434                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ /api/tags   │  │ /api/chat   │  │  /api/embeddings    │  │
│  │ 模型列表    │  │ 對話 API    │  │  向量化 API         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 程式碼區塊劃分

主程式 `ollama-chat.py` 分為 6 大區塊：

| 區塊 | 行數範圍 | 功能 |
|------|---------|------|
| Ollama helpers | 22-39 | 模型查詢、參數構建 |
| Embedding & RAG | 42-105 | 向量化、文件分塊、檢索 |
| Chat | 108-152 | 對話 API、Fallback 機制 |
| History | 155-165 | 對話紀錄存取 |
| Commands | 168-280 | 指令處理函數 |
| Interactive | 283-389 | 主對話迴圈 |

---

## 模組實作詳解

### 4.1 Ollama Helpers

#### get_installed_models()

查詢本機已安裝的 Ollama 模型：

```python
def get_installed_models() -> list[str]:
    resp = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return [m["name"] for m in data.get("models", [])]
```

**設計考量**：
- 使用 10 秒超時避免長時間阻塞
- 返回模型名稱列表供 Fallback 鏈驗證

#### build_options()

構建生成參數字典（僅包含非 None 值）：

```python
def build_options(temperature, top_p, num_ctx) -> dict:
    opts = {}
    if temperature is not None:
        opts["temperature"] = temperature
    if top_p is not None:
        opts["top_p"] = top_p
    if num_ctx is not None:
        opts["num_ctx"] = num_ctx
    return opts
```

### 4.2 Embedding & RAG

#### 向量化流程

```
文件目錄
    │
    ▼
load_documents()  ──────────────────────────────────┐
    │                                               │
    ├── .md/.txt 檔案 → read_text()                 │
    │                                               │
    └── .pdf 檔案 → pdf_loader.load_pdfs_from_dir() │
                                                    │
    ┌───────────────────────────────────────────────┘
    │
    ▼
chunk_text(doc, size=500)
    │
    │  按行切分，每 chunk 約 500 字元
    │
    ▼
embed_text(chunk)
    │
    │  POST /api/embeddings
    │  model: nomic-embed-text
    │
    ▼
index.append({"text": chunk, "embedding": vector})
```

#### cosine_similarity()

手動實作餘弦相似度（避免 numpy 依賴）：

```python
def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb + 1e-9)  # 加 epsilon 避免除零
```

#### retrieve_context()

檢索與查詢最相關的 Top-K 文件片段：

```python
def retrieve_context(query: str, index: list[dict], k: int) -> str:
    q_emb = embed_text(query)
    scored = [
        (cosine_similarity(q_emb, item["embedding"]), item["text"])
        for item in index
    ]
    scored.sort(reverse=True, key=lambda x: x[0])
    return "\n---\n".join(t for _, t in scored[:k])
```

### 4.3 Chat API

#### chat_once()

單次對話請求，支援 Streaming 與非 Streaming 模式：

```python
def chat_once(model, messages, stream, options) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "stream": stream,
    }
    if options:
        payload["options"] = options

    resp = requests.post(
        f"{OLLAMA_HOST}/api/chat",
        json=payload,
        stream=stream,
        timeout=600,
    )
    resp.raise_for_status()

    if not stream:
        return resp.json()["message"]["content"]

    # Streaming: 逐行解析 NDJSON
    full = []
    for line in resp.iter_lines():
        if not line:
            continue
        data = json.loads(line)
        if "message" in data and "content" in data["message"]:
            token = data["message"]["content"]
            print(token, end="", flush=True)
            full.append(token)
    print()
    return "".join(full)
```

**Streaming 實作細節**：
- 使用 `resp.iter_lines()` 逐行讀取
- 每行是一個完整的 JSON 物件（NDJSON 格式）
- `flush=True` 確保立即輸出

#### chat_with_fallback()

Fallback 模型鏈機制：

```python
def chat_with_fallback(models, messages, stream, options) -> str:
    last = None
    for m in models:
        try:
            print(f"\n🔄 使用模型：{m}\n")
            return chat_once(m, messages, stream, options)
        except Exception as e:
            print(f"⚠️  {m} 失敗：{e}", file=sys.stderr)
            last = e
    raise RuntimeError(last)
```

**設計考量**：
- 依序嘗試模型鏈中的每個模型
- 任何模型成功即返回
- 全部失敗時拋出最後一個例外

### 4.4 PDF Loader 模組

獨立模組設計，提供優雅降級能力：

```python
# pdf_loader.py

try:
    from pypdf import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


def is_available() -> bool:
    """檢查 PDF 支援是否可用"""
    return PDF_AVAILABLE


def load_pdf(path: Path, page_separator: str = "\n\n") -> Optional[str]:
    """讀取單一 PDF 文件"""
    if not PDF_AVAILABLE:
        return None
    try:
        reader = PdfReader(path)
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text.strip())
        return page_separator.join(pages) if pages else None
    except Exception as e:
        print(f"⚠️  無法讀取 PDF {path}: {e}")
        return None


def load_pdfs_from_dir(directory: Path) -> list[str]:
    """從目錄讀取所有 PDF 文件"""
    if not PDF_AVAILABLE:
        return []
    docs = []
    for p in directory.rglob("*.pdf"):
        if p.is_file():
            content = load_pdf(p)
            if content:
                docs.append(content)
    return docs
```

---

## 指令系統實作

### 指令分派架構

```python
# 主迴圈中的指令處理
if user_input.startswith("/"):
    parts = user_input.split(maxsplit=1)
    cmd = parts[0].lower()
    cmd_arg = parts[1] if len(parts) > 1 else None

    if cmd in {"/exit", "/quit"}:
        break
    elif cmd in {"/help", "/h"}:
        cmd_help()
    elif cmd == "/clear":
        messages = cmd_clear(messages, system_prompt)
    # ... 其他指令
    else:
        print(f"⚠️  未知指令：{cmd}")
    continue
```

### 各指令實作

#### /clear - 清除對話歷史

```python
def cmd_clear(messages: list, system_prompt: str | None) -> list:
    messages.clear()
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    print("🗑️  對話歷史已清除")
    return messages
```

**設計考量**：保留 system prompt，僅清除對話內容。

#### /redo - 重新生成回應

```python
def cmd_redo(messages: list, args, rag_index) -> tuple[list, str | None]:
    # 找到最後一個 user 訊息的位置
    last_user_idx = None
    for i in range(len(messages) - 1, -1, -1):
        if messages[i]["role"] == "user":
            last_user_idx = i
            break

    if last_user_idx is None:
        print("⚠️  沒有可重新生成的對話")
        return messages, None

    # 移除最後一個 user 之後的所有訊息
    messages = messages[:last_user_idx + 1]

    # 重新生成
    reply = chat_with_fallback(args.model_chain, messages, args.stream, args.options)
    messages.append({"role": "assistant", "content": reply})
    return messages, reply
```

**設計考量**：
- 從後往前搜尋最後一個 user 訊息
- 移除該訊息之後的所有內容（包括 assistant 回應）
- 重新呼叫 LLM 生成新回應

#### /status - 狀態總覽

```python
def cmd_status(args, messages: list, rag_index):
    print("📌 當前狀態：")
    print(f"   模型鏈：{' → '.join(args.model_chain)}")
    print(f"   Streaming：{'啟用' if args.stream else '停用'}")
    print(f"   RAG：{'啟用 (' + str(len(rag_index)) + ' chunks)' if rag_index else '停用'}")
    print(f"   Autosave：{'啟用 → ' + str(args.save) if args.autosave else '停用'}")
    print(f"   對話訊息：{len(messages)} 筆")
    if args.options:
        print(f"   生成參數：{args.options}")
```

### 完整指令列表

| 指令 | 參數 | 功能 |
|------|------|------|
| `/help`, `/h` | - | 顯示幫助訊息 |
| `/exit`, `/quit` | - | 退出程式 |
| `/clear` | - | 清除對話歷史 |
| `/history` | - | 顯示對話摘要 |
| `/redo` | - | 重新生成最後回應 |
| `/save` | `[path]` | 儲存對話 |
| `/load` | `<path>` | 載入對話 |
| `/model` | - | 顯示當前模型鏈 |
| `/models` | - | 列出可用模型 |
| `/status` | - | 顯示完整狀態 |

---

## 設計決策與考量

### 6.1 單檔案 vs 模組化

**決策**：核心功能保持單檔案，可選功能（PDF）獨立模組。

**理由**：
- 單檔案便於分享與部署
- 模組化允許功能擴展而不增加核心依賴
- 優雅降級：缺少模組時核心功能不受影響

### 6.2 Fallback 機制

**決策**：支援多層 Fallback 模型鏈。

**使用場景**：
- 主模型 OOM（記憶體不足）
- 主模型 timeout
- 主模型服務異常

**實作**：依序嘗試，任一成功即返回。

### 6.3 指令前綴

**決策**：使用 `/` 作為指令前綴。

**理由**：
- 避免與正常對話內容混淆
- 符合 CLI 工具慣例（如 IRC、Discord）
- 易於擴展新指令

### 6.4 RAG 純記憶體索引

**決策**：不持久化向量索引。

**理由**：
- 簡化實作
- 避免額外依賴（SQLite、FAISS）
- 適合中小型文件集合

**限制**：重啟需重建索引。

### 6.5 Streaming 實時輸出

**決策**：使用 `iter_lines()` 逐行解析 NDJSON。

**優點**：
- Token 級實時顯示
- 使用者體驗佳
- 適合長回應

### 6.6 時間戳儲存路徑

**決策**：`--autosave` 預設使用 `chats/YYYY-MM-DD-HH-mm-ss.json`。

**理由**：
- 自動避免覆蓋
- 便於按時間排序
- 減少使用者配置負擔

---

## 未來展望

### 已完成的 Roadmap

- ✅ PDF loader（pypdf）

### 待實作功能

| 功能 | 優先級 | 說明 |
|------|-------|------|
| SQLite 向量索引 | 高 | 持久化 RAG 索引 |
| FAISS 支援 | 中 | 高效向量搜尋 |
| FastAPI 服務 | 中 | HTTP API 介面 |
| Web UI | 低 | 瀏覽器介面 |
| 多使用者 | 低 | API Key 認證 |

### 架構演進方向

```
當前：單檔案 CLI
    │
    ▼
下一步：模組化重構
    │
    ├── core/         # 核心邏輯
    ├── loaders/      # 文件讀取器
    ├── storage/      # 向量索引
    └── cli/          # 命令行介面
    │
    ▼
未來：服務化
    │
    ├── api/          # FastAPI 服務
    ├── web/          # 前端介面
    └── workers/      # 背景任務
```

---

## 附錄

### A. 對話紀錄 JSON 格式

```json
{
  "meta": {
    "model_chain": ["qwen3-vl:8b", "deepseek-r1:8b", "llama3.1:8b"],
    "options": {"temperature": 0.7},
    "created_at": "2026-02-05T12:00:00"
  },
  "messages": [
    {"role": "system", "content": "總是以繁體中文回應訊息"},
    {"role": "user", "content": "你好"},
    {"role": "assistant", "content": "你好！有什麼我可以幫助你的嗎？"}
  ]
}
```

### B. Ollama API 端點

| 端點 | 方法 | 用途 |
|------|------|------|
| `/api/tags` | GET | 取得已安裝模型列表 |
| `/api/chat` | POST | 對話請求 |
| `/api/embeddings` | POST | 文本向量化 |

### C. 環境變數

目前未使用環境變數，所有配置透過命令行參數傳入。

未來可考慮支援：
- `OLLAMA_HOST`：Ollama 服務位址
- `OLLAMA_EMBED_MODEL`：預設 Embedding 模型

---

*文檔最後更新：2026-02-05*
