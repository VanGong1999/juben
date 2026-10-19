"""
LLM Wiki 工具：wiki_read / wiki_search / raw_read / wiki_ingest

配合 L1 index.md 常驻 prompt：
  index（已在 system）→ wiki_read → raw_read
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .types import ToolCategory, ToolContext, ToolDefinition, ToolResult, ToolUpdateCallback


def _tool_wiki_read() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        from utils.llm_wiki import ensure_wiki_bootstrapped, get_llm_wiki_store

        ensure_wiki_bootstrapped()
        path = str(params.get("path") or params.get("slug") or "").strip()
        if not path:
            return ToolResult.fail("path 必填（如 craft/cliffhanger.md 或 cliffhanger）")
        store = get_llm_wiki_store()
        result = store.read_wiki_page(path, max_chars=int(params.get("max_chars") or 20000))
        if not result.get("ok"):
            return ToolResult.fail(result.get("error") or "读取失败")
        sources = result.get("sources") or []
        hint = ""
        if sources:
            hint = (
                "\n\n---\n本页引用原文： "
                + ", ".join(f"`raw/{s}`" for s in sources)
                + "。若仍不够，调用 `raw_read`。"
            )
        return ToolResult.text(
            result["content"] + hint,
            details={
                "path": result.get("path"),
                "sources": sources,
                "tier": "L2",
                "truncated": result.get("truncated"),
            },
        )

    return ToolDefinition(
        name="wiki_read",
        label="读取 Wiki 页",
        description=(
            "按路径/slug 读取知识库 L2 wiki 页全文。"
            "先根据 system 中的 Knowledge Wiki Index（L1）定位页面，再调用本工具。"
            "例：path=craft/cliffhanger.md"
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "wiki 相对路径或 slug，如 craft/cliffhanger.md",
                },
                "slug": {"type": "string", "description": "可选，等同 path"},
                "max_chars": {"type": "integer", "default": 20000},
            },
            "required": ["path"],
        },
        execute=execute,
        category=ToolCategory.PREBUILT,
        always_load=True,  # 有 index 时常要读页，schema 很小
        tags=["wiki", "knowledge", "L2"],
    )


def _tool_wiki_search() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        from utils.llm_wiki import ensure_wiki_bootstrapped, get_llm_wiki_store

        ensure_wiki_bootstrapped()
        query = str(params.get("query") or "").strip()
        if not query:
            return ToolResult.fail("query 必填")
        store = get_llm_wiki_store()
        hits = store.search_index(query, limit=int(params.get("limit") or 8))
        if not hits:
            return ToolResult.text(
                "index 无匹配。可浏览 system 中的 Wiki Index，或换关键词。",
                details={"query": query, "count": 0},
            )
        lines = [f"Wiki 检索「{query}」（来自 index，未加载全文）："]
        for p in hits:
            lines.append(f"- [[{p.path}]] — {p.summary}")
        lines.append("\n需要细节请 `wiki_read(path=...)`。")
        return ToolResult.text(
            "\n".join(lines),
            details={"query": query, "paths": [p.path for p in hits], "tier": "L1"},
        )

    return ToolDefinition(
        name="wiki_search",
        label="搜索 Wiki 目录",
        description=(
            "在 L1 index 中按关键词筛选 wiki 页（只返回链接+摘要，不加载正文）。"
            "找到候选后再 wiki_read。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 8},
            },
            "required": ["query"],
        },
        execute=execute,
        category=ToolCategory.PREBUILT,
        always_load=True,
        tags=["wiki", "knowledge", "L1"],
    )


def _tool_raw_read() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        from utils.llm_wiki import ensure_wiki_bootstrapped, get_llm_wiki_store

        ensure_wiki_bootstrapped()
        path = str(params.get("path") or "").strip()
        if not path:
            return ToolResult.fail("path 必填（相对 raw/，如 craft/hook-paywall-notes.txt）")
        store = get_llm_wiki_store()
        result = store.read_raw(path, max_chars=int(params.get("max_chars") or 30000))
        if not result.get("ok"):
            return ToolResult.fail(result.get("error") or "读取失败")
        return ToolResult.text(
            f"# raw/{result['path']}\n\n{result['content']}",
            details={"path": result.get("path"), "tier": "L3", "truncated": result.get("truncated")},
        )

    return ToolDefinition(
        name="raw_read",
        label="读取原文",
        description=(
            "读取知识库 L3 原始文档（raw/）。"
            "**仅当 wiki 页信息不够时**再调用；优先 wiki_read。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "相对 raw/ 的路径"},
                "max_chars": {"type": "integer", "default": 30000},
            },
            "required": ["path"],
        },
        execute=execute,
        category=ToolCategory.PREBUILT,
        always_load=False,  # deferred：名录提示即可
        tags=["wiki", "knowledge", "L3", "raw"],
    )


def _tool_wiki_ingest() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        from utils.llm_wiki import ensure_wiki_bootstrapped, get_llm_wiki_store

        ensure_wiki_bootstrapped()
        store = get_llm_wiki_store()
        raw_path = str(params.get("raw_path") or "").strip()
        content = params.get("content")
        title = str(params.get("title") or "").strip()
        summary = str(params.get("summary") or "").strip()
        category = str(params.get("category") or "sources").strip()
        slug = str(params.get("slug") or "").strip()
        wiki_body = str(params.get("wiki_body") or "").strip()

        if content and raw_path:
            wr = store.write_raw(raw_path, str(content), overwrite=bool(params.get("overwrite")))
            if not wr.get("ok"):
                return ToolResult.fail(wr.get("error") or "写入 raw 失败")

        if not title or not summary or not wiki_body:
            # 仅写入 raw / 或仅重建
            if params.get("rebuild_only"):
                store.rebuild_index()
                return ToolResult.text("已重建 index.md", details={"action": "rebuild_index"})
            if content and raw_path and not wiki_body:
                return ToolResult.text(
                    f"已写入 raw/{raw_path}。请补充 title/summary/wiki_body 以生成 wiki 页。",
                    details={"raw_path": raw_path},
                )
            return ToolResult.fail("需要 title、summary、wiki_body 以创建 wiki 页")

        if not slug:
            slug = title.lower().replace(" ", "-")[:48]
        sources = [raw_path] if raw_path else list(params.get("sources") or [])
        out = store.write_wiki_page(
            category=category,
            slug=slug,
            title=title,
            summary=summary,
            body=wiki_body,
            tags=list(params.get("tags") or []),
            sources=sources,
            cache_tier=str(params.get("cache_tier") or "L3"),
            rebuild_index=True,
        )
        if not out.get("ok"):
            return ToolResult.fail(out.get("error") or "写入 wiki 失败")
        return ToolResult.text(
            f"已入库 wiki/{out['path']}，并更新 index.md。"
            + (f" 原文: raw/{raw_path}" if raw_path else ""),
            details=out,
        )

    return ToolDefinition(
        name="wiki_ingest",
        label="入库 Wiki",
        description=(
            "将资料写入 raw/（可选）并创建/更新 wiki 页，自动重建 index.md。"
            "用于把新知识纳入三级缓存体系。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "raw_path": {"type": "string", "description": "原文相对 raw/ 路径"},
                "content": {"type": "string", "description": "原文内容（与 raw_path 一起）"},
                "overwrite": {"type": "boolean", "default": False},
                "title": {"type": "string"},
                "summary": {"type": "string", "description": "一句话摘要（写入 index）"},
                "slug": {"type": "string"},
                "category": {
                    "type": "string",
                    "description": "craft|concepts|entities|sources|…",
                    "default": "sources",
                },
                "wiki_body": {"type": "string", "description": "wiki 页 Markdown 正文"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "cache_tier": {"type": "string", "default": "L3"},
                "rebuild_only": {"type": "boolean", "default": False},
            },
            "required": [],
        },
        execute=execute,
        category=ToolCategory.EXTERNAL,
        dangerous=True,
        always_load=False,
        tags=["wiki", "knowledge", "ingest"],
    )


def get_wiki_tools() -> List[ToolDefinition]:
    return [
        _tool_wiki_read(),
        _tool_wiki_search(),
        _tool_raw_read(),
        _tool_wiki_ingest(),
    ]
