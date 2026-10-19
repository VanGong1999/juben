"""
LLM Wiki — 三级知识缓存（对齐 Karpathy / llm-wiki）

L1 index.md  — 常驻 prompt：每页一行链接 + 一句话摘要
L2 wiki/*    — 按需读取的整理页（概念 / 实体 / 技法 / 来源摘要）
L3 raw/*     — 不可变原文；仅当 wiki 不够时再下钻

Agent 导航：读 index → wiki_read →（必要时）raw_read
"""

from .store import LlmWikiStore, get_llm_wiki_store
from .prompt import build_wiki_index_prompt, ensure_wiki_bootstrapped

__all__ = [
    "LlmWikiStore",
    "get_llm_wiki_store",
    "build_wiki_index_prompt",
    "ensure_wiki_bootstrapped",
]
