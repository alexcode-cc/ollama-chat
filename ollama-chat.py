#!/usr/bin/env python3
import requests
import argparse
import sys
import json
import math
import threading
import time
import atexit
import csv
import re
from typing import Optional, List, Dict
from datetime import datetime, timezone
from pathlib import Path

# Readline 支援（行編輯、歷史記錄、方向鍵）
try:
    import readline
    READLINE_AVAILABLE = True
except ImportError:
    try:
        # Windows 需要 pyreadline3
        import pyreadline3 as readline
        READLINE_AVAILABLE = True
    except ImportError:
        READLINE_AVAILABLE = False

# 設定輸入歷史檔案
if READLINE_AVAILABLE:
    HISTORY_FILE = Path.home() / ".ollama_chat_history"
    try:
        readline.read_history_file(HISTORY_FILE)
        readline.set_history_length(1000)
    except FileNotFoundError:
        pass
    atexit.register(readline.write_history_file, HISTORY_FILE)

try:
    import pdf_loader
    PDF_SUPPORT = pdf_loader.is_available()
except ImportError:
    PDF_SUPPORT = False


OLLAMA_HOST = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"


# ---------- Ollama helpers ----------

def get_installed_models() -> list[str]:
    resp = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return [m["name"] for m in data.get("models", [])]


def build_options(temperature, top_p, num_ctx) -> dict:
    opts = {}
    if temperature is not None:
        opts["temperature"] = temperature
    if top_p is not None:
        opts["top_p"] = top_p
    if num_ctx is not None:
        opts["num_ctx"] = num_ctx
    return opts


# ---------- Embedding & RAG ----------

def embed_text(text: str) -> list[float]:
    resp = requests.post(
        f"{OLLAMA_HOST}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb + 1e-9)


def chunk_text(text: str, size: int = 500) -> list[str]:
    chunks = []
    buf = ""
    for line in text.splitlines():
        if len(buf) + len(line) > size:
            chunks.append(buf)
            buf = ""
        buf += line + "\n"
    if buf.strip():
        chunks.append(buf)
    return chunks


def load_documents(path: Path) -> list[str]:
    docs = []
    for p in path.rglob("*"):
        if p.suffix.lower() in {".md", ".txt"} and p.is_file():
            docs.append(p.read_text(encoding="utf-8", errors="ignore"))
    # PDF 支援
    if PDF_SUPPORT:
        docs.extend(pdf_loader.load_pdfs_from_dir(path))
    return docs


def build_rag_index(path: Path) -> list[dict]:
    index = []
    for doc in load_documents(path):
        for chunk in chunk_text(doc):
            emb = embed_text(chunk)
            index.append({"text": chunk, "embedding": emb})
    return index


def retrieve_context(
    query: str,
    index: list[dict],
    k: int,
) -> str:
    q_emb = embed_text(query)
    scored = [
        (cosine_similarity(q_emb, item["embedding"]), item["text"])
        for item in index
    ]
    scored.sort(reverse=True, key=lambda x: x[0])
    return "\n---\n".join(t for _, t in scored[:k])


# ---------- Spinner ----------

class Spinner:
    """等待時顯示旋轉動畫"""
    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, message: str = "思考中"):
        self.message = message
        self.running = False
        self.thread = None

    def _spin(self):
        idx = 0
        while self.running:
            frame = self.FRAMES[idx % len(self.FRAMES)]
            print(f"\r{frame} {self.message}...", end="", flush=True)
            idx += 1
            time.sleep(0.1)

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._spin, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=0.2)
        print("\r" + " " * (len(self.message) + 10) + "\r", end="", flush=True)


# ---------- Chat ----------

def chat_once(model, messages, stream, options, spinner: Spinner = None) -> str:
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
        content = resp.json()["message"]["content"]
        if spinner:
            spinner.stop()
        return content

    full = []
    first_token = True
    for line in resp.iter_lines():
        if not line:
            continue
        data = json.loads(line)
        if "message" in data and "content" in data["message"]:
            if first_token and spinner:
                spinner.stop()
                first_token = False
            token = data["message"]["content"]
            print(token, end="", flush=True)
            full.append(token)
    print()
    return "".join(full)


def chat_with_fallback(models, messages, stream, options) -> str:
    last = None
    for m in models:
        try:
            print(f"\n🔄 使用模型：{m}\n")
            spinner = Spinner("思考中")
            spinner.start()
            try:
                return chat_once(m, messages, stream, options, spinner)
            finally:
                spinner.stop()
        except Exception as e:
            print(f"⚠️  {m} 失敗：{e}", file=sys.stderr)
            last = e
    raise RuntimeError(last)


# ---------- History ----------

def save_history(path: Path, meta: dict, messages: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"meta": meta, "messages": messages}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_history(path: Path) -> tuple[dict, list[dict]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw.get("meta", {}), raw.get("messages", [])


def convert_json_to_csv(json_path: Path) -> Path:
    """將 JSON 對話記錄轉換為 CSV 格式"""
    if not json_path.exists():
        raise FileNotFoundError(f"檔案不存在：{json_path}")

    meta, messages = load_history(json_path)

    # 產生 CSV 檔案路徑（同檔名，副檔名改為 .csv）
    csv_path = json_path.with_suffix(".csv")

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # 寫入標題列
        writer.writerow(["index", "role", "content"])
        # 寫入對話記錄
        for i, msg in enumerate(messages, 1):
            writer.writerow([i, msg.get("role", ""), msg.get("content", "")])

    return csv_path


# ---------- Commands ----------

HELP_TEXT = """
📖 可用指令：

  /help, /h        顯示此幫助訊息
  /exit, /quit     退出程式

  /clear           清除對話歷史（保留 system prompt）
  /history         顯示對話歷史摘要
  /history-all     顯示完整對話記錄
  /redo            重新生成最後一次回應

  /save [path]     儲存對話（可選路徑，預設時間戳）
  /load <path>     載入對話歷史

  /model           顯示當前模型鏈
  /models          顯示所有可用模型
  /status          顯示當前狀態
""".strip()


def cmd_help():
    print(HELP_TEXT)


def cmd_clear(messages: list, system_prompt: str | None) -> list:
    messages.clear()
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    print("🗑️  對話歷史已清除")
    return messages


def cmd_history(messages: list):
    user_count = sum(1 for m in messages if m["role"] == "user")
    assistant_count = sum(1 for m in messages if m["role"] == "assistant")
    system_count = sum(1 for m in messages if m["role"] == "system")
    print(f"📊 對話歷史：{len(messages)} 筆訊息")
    print(f"   system: {system_count}, user: {user_count}, assistant: {assistant_count}")
    if messages:
        last = messages[-1]
        preview = last["content"][:50] + "..." if len(last["content"]) > 50 else last["content"]
        print(f"   最後一筆 [{last['role']}]: {preview}")


def cmd_history_all(messages: list):
    """顯示完整對話記錄"""
    if not messages:
        print("📭 目前沒有對話記錄")
        return

    print("=" * 60)
    print("📜 完整對話記錄")
    print("=" * 60)

    for i, msg in enumerate(messages, 1):
        role = msg["role"]
        content = msg["content"]

        if role == "system":
            print(f"\n[{i}] 🔧 System:")
            print(f"    {content[:200]}{'...' if len(content) > 200 else ''}")
        elif role == "user":
            print(f"\n[{i}] 🧑 User:")
            print(f"    {content}")
        elif role == "assistant":
            print(f"\n[{i}] 🤖 Assistant:")
            # 對於長回應，顯示前 500 字元
            if len(content) > 500:
                print(f"    {content[:500]}...")
                print(f"    （共 {len(content)} 字元）")
            else:
                print(f"    {content}")

    print("\n" + "=" * 60)


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

    # 移除最後一個 user 之後的所有訊息（包括 assistant 回應）
    messages = messages[:last_user_idx + 1]

    # 重新生成
    reply = chat_with_fallback(
        args.model_chain,
        messages,
        args.stream,
        args.options,
    )
    messages.append({"role": "assistant", "content": reply})
    return messages, reply


def cmd_save(messages: list, meta: dict, path_arg: str | None):
    if path_arg:
        path = Path(path_arg)
    else:
        path = Path("chats") / (datetime.now().strftime("%Y-%m-%d-%H-%M-%S") + ".json")
    save_history(path, meta, messages)
    print(f"💾 對話已儲存：{path}")


def cmd_load(path_arg: str | None, system_prompt: str | None) -> tuple[list, bool]:
    if not path_arg:
        print("⚠️  請指定檔案路徑，例如：/load chats/xxx.json")
        return [], False
    path = Path(path_arg)
    if not path.exists():
        print(f"⚠️  檔案不存在：{path}")
        return [], False
    _, messages = load_history(path)
    print(f"📂 已載入 {len(messages)} 筆訊息：{path}")
    return messages, True


def cmd_model(args, meta, messages, cmd_arg: str | None):
    if not cmd_arg:
        print(f"🤖 模型鏈：{' → '.join(args.model_chain)}")
        return

    installed = get_installed_models()
    if cmd_arg not in installed:
        print(f"⚠️  模型 '{cmd_arg}' 不可用")
        print(f"💡 使用 /models 查看可用模型")
        return

    # 切換前將當前對話儲存到既有路徑（避免數據遺失）
    if args.autosave and args.save and args.save.exists():
        save_history(args.save, meta, messages)

    args.model_chain = [cmd_arg]
    meta["model_chain"] = args.model_chain
    print(f"🔄 已切換模型：{cmd_arg}")

    # 自動生成的路徑需隨模型名更新
    if args.autosave and getattr(args, '_save_is_auto', False):
        safe_model_name = re.sub(r'[:\\/*?"<>|]', '-', cmd_arg)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        args.save = Path("chats") / f"{safe_model_name}_{timestamp}.json"
        print(f"💾 自動存檔路徑更新：{args.save}")


def cmd_models():
    models = get_installed_models()
    print(f"📋 可用模型（{len(models)} 個）：")
    for m in models:
        print(f"   • {m}")


def cmd_status(args, messages: list, rag_index):
    print("📌 當前狀態：")
    print(f"   模型鏈：{' → '.join(args.model_chain)}")
    print(f"   Streaming：{'啟用' if args.stream else '停用'}")
    print(f"   RAG：{'啟用 (' + str(len(rag_index)) + ' chunks)' if rag_index else '停用'}")
    print(f"   Autosave：{'啟用 → ' + str(args.save) if args.autosave else '停用'}")
    print(f"   對話訊息：{len(messages)} 筆")
    if args.options:
        print(f"   生成參數：{args.options}")


# ---------- Interactive ----------

def interactive_chat(args):
    meta = {
        "model_chain": args.model_chain,
        "options": args.options,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    if args.load:
        print(f"📂 載入歷史紀錄：{args.load}")
        if not args.load.exists():
            print(f"❌ 檔案不存在：{args.load}")
            print("💡 將以空白對話開始")
            messages = []
        else:
            try:
                _, messages = load_history(args.load)
                print(f"✅ 載入 {len(messages)} 筆訊息")
                # 顯示載入的對話記錄
                if messages:
                    cmd_history_all(messages)
            except json.JSONDecodeError as e:
                print(f"❌ 檔案格式錯誤：{e}")
                print("💡 將以空白對話開始")
                messages = []
            except Exception as e:
                print(f"❌ 載入失敗：{e}")
                print("💡 將以空白對話開始")
                messages = []
    else:
        messages = []

    rag_index = None
    if args.rag:
        print("📚 建立 RAG index...")
        if PDF_SUPPORT:
            print("📄 PDF 支援：已啟用")
        else:
            print("📄 PDF 支援：未啟用（pip install pypdf）")
        rag_index = build_rag_index(args.rag)
        print(f"✅ RAG chunks: {len(rag_index)}")

    system_prompt = args.system
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    if args.autosave and args.save:
        print(f"💾 autosave 啟用：{args.save}")

    print("💬 進入對話模式（輸入 /help 查看指令）\n")

    while True:
        try:
            user_input = input("🧑 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue

        # 指令處理
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
            elif cmd == "/history":
                cmd_history(messages)
            elif cmd == "/history-all":
                cmd_history_all(messages)
            elif cmd == "/redo":
                messages, reply = cmd_redo(messages, args, rag_index)
                if reply and args.autosave and args.save:
                    save_history(args.save, meta, messages)
            elif cmd == "/save":
                cmd_save(messages, meta, cmd_arg)
            elif cmd == "/load":
                loaded, ok = cmd_load(cmd_arg, system_prompt)
                if ok:
                    messages = loaded
            elif cmd == "/model":
                cmd_model(args, meta, messages, cmd_arg)
            elif cmd == "/models":
                cmd_models()
            elif cmd == "/status":
                cmd_status(args, messages, rag_index)
            else:
                print(f"⚠️  未知指令：{cmd}（輸入 /help 查看可用指令）")
            continue

        # 正常對話
        if rag_index:
            context = retrieve_context(user_input, rag_index, args.rag_k)
            messages.append({
                "role": "system",
                "content": f"以下內容來自文件，請優先依據回答：\n{context}",
            })

        messages.append({"role": "user", "content": user_input})

        try:
            reply = chat_with_fallback(
                args.model_chain,
                messages,
                args.stream,
                args.options,
            )
            messages.append({"role": "assistant", "content": reply})

            if args.autosave and args.save:
                save_history(args.save, meta, messages)
        except Exception as e:
            print(f"❌ 對話失敗：{e}", file=sys.stderr)
            messages.pop()  # 移除剛加入的 user 訊息

    if args.save:
        save_history(args.save, meta, messages)
        print(f"💾 對話已儲存：{args.save}")


# ---------- Main ----------

class _CountAction(argparse.Action):
    """追蹤參數被設置的次數，用於檢測用戶是否覆蓋了腳本預設值"""
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)
        setattr(namespace, f'_{self.dest}_count',
                getattr(namespace, f'_{self.dest}_count', 0) + 1)


def main():
    parser = argparse.ArgumentParser(
        description="Ollama Chat CLI with RAG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
覆蓋預設參數範例（搭配啟動腳本使用）：
  chat.sh --model deepseek-r1:8b      # 覆蓋模型（自動排除預設 fallback）
  chat.sh --model x --fallback y      # 覆蓋模型並自訂 fallback 鏈
  chat.sh --no-stream                 # 取消 streaming
  chat.sh --no-autosave               # 取消自動儲存
  chat.sh --system "新的提示詞"       # 覆蓋系統提示詞
  chat.sh --no-default-fallback       # 明確排除預設 fallback 模型
        """,
    )

    parser.add_argument("--model", action=_CountAction, default="llama3.1:8b")
    parser.add_argument("--fallback", action="append", default=[],
                        help="備援模型（可多個）")
    parser.add_argument("--default-fallback", action="append", default=[],
                        help="預設備援模型（由啟動腳本設定）")
    parser.add_argument("--no-default-fallback", action="store_true",
                        help="明確排除預設 fallback 模型")
    parser.add_argument("--stream", action=argparse.BooleanOptionalAction, default=False,
                        help="啟用/停用流式輸出（--stream / --no-stream）")
    parser.add_argument("--system")

    parser.add_argument("--rag", type=Path, help="RAG document folder")
    parser.add_argument("--rag-k", type=int, default=4)

    parser.add_argument("--temperature", type=float)
    parser.add_argument("--top-p", type=float, dest="top_p")
    parser.add_argument("--num-ctx", type=int, dest="num_ctx")

    parser.add_argument("--save", type=Path, help="儲存對話紀錄路徑")
    parser.add_argument("--load", type=Path, help="載入歷史對話路徑")
    parser.add_argument("--autosave", action=argparse.BooleanOptionalAction, default=False,
                        help="啟用/停用每輪自動儲存（--autosave / --no-autosave）")
    parser.add_argument("--convert", type=Path, help="將 JSON 對話記錄轉換為 CSV")

    args = parser.parse_args()

    # 合併 fallback 邏輯：
    #   - --model 被覆蓋（腳本＋用戶各傳一次）→ 自動排除 default-fallback
    #   - --no-default-fallback → 明確排除 default-fallback
    #   - 其它情況 → 合併用戶 fallback + 預設 fallback
    _model_overridden = getattr(args, '_model_count', 0) > 1
    if not args.no_default_fallback and not _model_overridden:
        args.fallback = args.fallback + args.default_fallback

    # 處理 --convert 參數（轉換後直接退出）
    if args.convert:
        try:
            csv_path = convert_json_to_csv(args.convert)
            print(f"✅ 轉換完成：{args.convert} → {csv_path}")
        except FileNotFoundError as e:
            print(f"❌ {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"❌ 轉換失敗：{e}", file=sys.stderr)
            sys.exit(1)
        return

    installed = set(get_installed_models())
    chain = [args.model] + args.fallback
    args.model_chain = [m for m in chain if m in installed]

    # 處理 autosave 預設路徑
    args._save_is_auto = False
    if args.autosave and not args.save:
        if args.load:
            # 使用 --load 時，autosave 儲存到同一檔案
            args.save = args.load
        else:
            # 使用模型名稱 + 時間戳作為檔名
            model_name = args.model_chain[0] if args.model_chain else args.model
            # 清理模型名稱中的不合法字元
            safe_model_name = re.sub(r'[:\\/*?"<>|]', '-', model_name)
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            args.save = Path("chats") / f"{safe_model_name}_{timestamp}.json"
            args._save_is_auto = True

    args.options = build_options(
        args.temperature,
        args.top_p,
        args.num_ctx,
    )

    interactive_chat(args)


if __name__ == "__main__":
    main()
