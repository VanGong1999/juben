"""
L1：把 wiki/index.md 注入 prompt（常驻、可缓存前缀侧）
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .store import get_llm_wiki_store


def build_wiki_index_prompt(*, max_chars: int = 6000, root: Optional[Path] = None) -> str:
    """
    返回应常驻 system 的 L1 块。
    Agent 每次会话都能看到「有哪些知识」，但不装全文。
    """
    store = get_llm_wiki_store(root)
    store.ensure_layout()
    index = store.read_index(max_chars=max_chars)
    return (
        "## Knowledge Wiki Index (L1 · always loaded)\n"
        "导航规则：根据下列目录定位页面 → 调用 `wiki_read` → "
        "若仍不足再 `raw_read`。禁止假设未读取页的细节。\n\n"
        + index
    )


def ensure_wiki_bootstrapped(root: Optional[Path] = None) -> None:
    """确保目录存在；若 wiki 为空则写入种子页。"""
    from .bootstrap_seed import seed_if_empty

    store = get_llm_wiki_store(root)
    store.ensure_layout()
    seed_if_empty(store)
