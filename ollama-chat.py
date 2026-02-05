#!/usr/bin/env python3
import requests
import argparse
import sys
import json
import math
from typing import Optional, List, Dict
from datetime import datetime
from pathlib import Path


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


# ---------- Chat ----------

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


# ---------- Interactive ----------

def interactive_chat(args):
    messages = []
    meta = {
        "model_chain": args.model_chain,
        "options": args.options,
        "created_at": datetime.utcnow().isoformat(),
    }

    rag_index = None
    if args.rag:
        print("📚 建立 RAG index...")
        rag_index = build_rag_index(args.rag)
        print(f"✅ RAG chunks: {len(rag_index)}")

    if args.system:
        messages.append({"role": "system", "content": args.system})

    print("💬 進入對話模式（exit / quit 離開）\n")

    while True:
        user_input = input("🧑 > ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue

        if rag_index:
            context = retrieve_context(user_input, rag_index, args.rag_k)
            messages.append({
                "role": "system",
                "content": f"以下內容來自文件，請優先依據回答：\n{context}",
            })

        messages.append({"role": "user", "content": user_input})

        reply = chat_with_fallback(
            args.model_chain,
            messages,
            args.stream,
            args.options,
        )
        messages.append({"role": "assistant", "content": reply})


# ---------- Main ----------

def main():
    parser = argparse.ArgumentParser(description="Ollama Chat CLI with RAG")

    parser.add_argument("--model", default="llama3.1:8b")
    parser.add_argument("--fallback", action="append", default=[])
    parser.add_argument("--stream", action="store_true")
    parser.add_argument("--system")

    parser.add_argument("--rag", type=Path, help="RAG document folder")
    parser.add_argument("--rag-k", type=int, default=4)

    parser.add_argument("--temperature", type=float)
    parser.add_argument("--top-p", type=float, dest="top_p")
    parser.add_argument("--num-ctx", type=int, dest="num_ctx")

    args = parser.parse_args()

    installed = set(get_installed_models())
    chain = [args.model] + args.fallback
    args.model_chain = [m for m in chain if m in installed]

    args.options = build_options(
        args.temperature,
        args.top_p,
        args.num_ctx,
    )

    interactive_chat(args)


if __name__ == "__main__":
    main()
