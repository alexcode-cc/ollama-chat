#!/usr/bin/env python3
"""
PDF Loader 模組

提供 PDF 文件讀取功能，支援多頁文件的文字提取。
使用 pypdf 庫解析 PDF。

安裝依賴：
    pip install pypdf
"""

from pathlib import Path
from typing import Optional

try:
    from pypdf import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


def is_available() -> bool:
    """檢查 PDF 支援是否可用"""
    return PDF_AVAILABLE


def load_pdf(path: Path, page_separator: str = "\n\n") -> Optional[str]:
    """
    讀取 PDF 文件並提取文字內容

    Args:
        path: PDF 文件路徑
        page_separator: 頁面之間的分隔符

    Returns:
        提取的文字內容，若失敗則返回 None
    """
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
    """
    從目錄中讀取所有 PDF 文件

    Args:
        directory: 目錄路徑

    Returns:
        所有 PDF 文件的文字內容列表
    """
    if not PDF_AVAILABLE:
        return []

    docs = []
    for p in directory.rglob("*.pdf"):
        if p.is_file():
            content = load_pdf(p)
            if content:
                docs.append(content)
    return docs
