"""
External tools — 原「工具类专家」能力，改为 Agent 可调用的工具
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .types import ToolCategory, ToolContext, ToolDefinition, ToolResult, ToolUpdateCallback


def _resolve_drama_id(ctx: Optional[ToolContext], params: Dict[str, Any]) -> Optional[str]:
    """作品级记忆隔离：优先 ctx.drama_id（API 层已校验归属），禁止 params 越权跨作品。

    模型/攻击者伪造 params.drama_id 与绑定作品不一致时返回 None，调用方应拒绝。
    """
    ctx_drama = getattr(ctx, "drama_id", None) if ctx else None
    param_drama = params.get("drama_id")
    if ctx_drama:
        if param_drama and param_drama != ctx_drama:
            return None
        return ctx_drama
    return param_drama


async def _run_web_search(query: str, top_k: int = 8) -> Dict[str, Any]:
    """优先 DeepSeek Search，失败再回退百度。"""
    import os

    provider = (os.getenv("WEB_SEARCH_PROVIDER") or "deepseek").strip().lower()
    errors: List[str] = []

    if provider != "baidu":
        try:
            from utils.deepseek_client import get_deepseek_client

            ds = get_deepseek_client()
            if ds.available:
                return await ds.web_search(query=query, top_k=top_k)
            errors.append("DEEPSEEK_API_KEY 未配置")
        except Exception as e:
            errors.append(f"deepseek: {e}")

    try:
        from utils.baidu_client import get_baidu_client

        return await get_baidu_client().web_search(query=query, top_k=top_k)
    except Exception as e:
        errors.append(f"baidu: {e}")
        raise RuntimeError("；".join(errors) or str(e)) from e


def _tool_web_search() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        query = (params.get("query") or "").strip()
        if not query:
            return ToolResult.fail("query 必填")
        top_k = int(params.get("top_k") or 8)
        try:
            raw = await _run_web_search(query=query, top_k=top_k)
            refs = raw.get("references") or []
            lines = []
            for i, ref in enumerate(refs, 1):
                lines.append(
                    f"{i}. {ref.get('title', '')}\n"
                    f"   URL: {ref.get('url', '')}\n"
                    f"   {ref.get('content', '')[:280]}"
                )
            text = "\n\n".join(lines) if lines else "未找到结果"
            return ToolResult.text(
                text,
                details={
                    "query": query,
                    "count": len(refs),
                    "provider": raw.get("provider") or "unknown",
                    "raw": raw,
                },
            )
        except Exception as e:
            return ToolResult.fail(str(e))

    return ToolDefinition(
        name="web_search",
        label="网络搜索",
        description="实时搜索网络信息（DeepSeek Search），获取最新资料。创作调研、竞品与题材验证时使用。",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"},
                "top_k": {"type": "integer", "default": 8},
            },
            "required": ["query"],
        },
        execute=execute,
        category=ToolCategory.EXTERNAL,
        dangerous=True,
        tags=["external", "search", "deepseek", "was_agent:websearch"],
    )


def _tool_web_fetch() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        url = (params.get("url") or "").strip()
        if not url:
            return ToolResult.fail("url 必填")
        try:
            from utils.deepseek_client import get_deepseek_client

            client = get_deepseek_client()
            if not client.available:
                return ToolResult.fail("未配置 DEEPSEEK_API_KEY")
            raw = await client.fetch(url=url)
            title = raw.get("title") or ""
            content = (raw.get("content") or "")[:12000]
            text = f"# {title}\n\n{content}" if title else content
            return ToolResult.text(text or "页面无正文", details={"url": url, "raw": raw})
        except Exception as e:
            return ToolResult.fail(str(e))

    return ToolDefinition(
        name="web_fetch",
        label="网页抓取",
        description="用 DeepSeek Fetch 抓取指定 URL，返回 Markdown 正文。配合 web_search 做深度调研。",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "要抓取的网页 URL"},
            },
            "required": ["url"],
        },
        execute=execute,
        category=ToolCategory.EXTERNAL,
        dangerous=True,
        tags=["external", "fetch", "deepseek"],
    )


def _tool_knowledge_query() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        query = (params.get("query") or "").strip()
        if not query:
            return ToolResult.fail("query 必填")
        top_k = int(params.get("top_k") or 5)
        try:
            from utils.knowledge_base_client import knowledge_base_client

            result = await knowledge_base_client.search(query=query, top_k=top_k)
            if isinstance(result, dict) and result.get("success") is False:
                return ToolResult.fail(result.get("error") or "知识库查询失败")
            items = (
                result
                if isinstance(result, list)
                else (result.get("results") or result.get("data") or [])
            )
            if isinstance(result, dict) and not items and result.get("answer"):
                return ToolResult.text(str(result["answer"]), details={"query": query})
            lines = []
            for i, it in enumerate(items[:top_k], 1):
                if isinstance(it, dict):
                    title = it.get("title") or it.get("source") or f"片段{i}"
                    body = it.get("content") or it.get("text") or it.get("snippet") or ""
                    lines.append(f"{i}. {title}\n{body[:400]}")
                else:
                    lines.append(f"{i}. {str(it)[:400]}")
            return ToolResult.text(
                "\n\n".join(lines) if lines else "知识库无命中",
                details={"query": query, "count": len(lines)},
            )
        except Exception as e:
            return ToolResult.fail(str(e))

    return ToolDefinition(
        name="knowledge_query",
        label="知识库向量检索",
        description=(
            "对原始知识片段做向量检索（兜底）。"
            "优先走 LLM Wiki：看 system 中的 index → wiki_read → raw_read；"
            "仅当 wiki 体系无相关页时再用本工具。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer", "default": 5},
            },
            "required": ["query"],
        },
        execute=execute,
        category=ToolCategory.EXTERNAL,
        always_load=False,
        tags=["external", "kb", "vector", "was_agent:knowledge"],
    )


def _tool_text_split() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        text = params.get("text") or ""
        chunk_size = int(params.get("chunk_size") or 2000)
        overlap = int(params.get("overlap") or 100)
        if not text:
            return ToolResult.fail("text 必填")
        try:
            from utils.text_processor import TextSplitter

            splitter = TextSplitter()
            chunks = await splitter.split_text(text, chunk_size=chunk_size, overlap=overlap)
            out = "\n\n---\n\n".join(f"[块 {i+1}/{len(chunks)}]\n{c}" for i, c in enumerate(chunks))
            return ToolResult.text(out, details={"chunks": len(chunks), "chunk_size": chunk_size})
        except Exception as e:
            return ToolResult.fail(str(e))

    return ToolDefinition(
        name="text_split",
        label="文本分割",
        description="将长文本智能分割为合适段落，便于分批处理。",
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "chunk_size": {"type": "integer", "default": 2000},
                "overlap": {"type": "integer", "default": 100},
            },
            "required": ["text"],
        },
        execute=execute,
        category=ToolCategory.EXTERNAL,
        tags=["external", "text", "was_agent:text_splitter"],
    )


def _tool_text_truncate() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        text = params.get("text") or ""
        max_length = int(params.get("max_length") or 8000)
        if not text:
            return ToolResult.fail("text 必填")
        try:
            from utils.text_processor import TextTruncator

            truncator = TextTruncator()
            out = await truncator.truncate_text(text, max_length=max_length)
            return ToolResult.text(out, details={"original": len(text), "result": len(out)})
        except Exception as e:
            return ToolResult.fail(str(e))

    return ToolDefinition(
        name="text_truncate",
        label="文本截断",
        description="按长度截断文本并尽量在句末保持完整。",
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "max_length": {"type": "integer", "default": 8000},
            },
            "required": ["text"],
        },
        execute=execute,
        category=ToolCategory.EXTERNAL,
        tags=["external", "text", "was_agent:text_truncator"],
    )


def _tool_extract_series_name() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        text = params.get("text") or ""
        if not text:
            return ToolResult.fail("text 必填")
        # 轻量启发式 + 可选 LLM 留给上层；工具侧保持确定性
        patterns = [
            r"[《「]([^》」]{1,40})[》」]",
            r"(?:剧名|短剧名|片名)[:：\s]*([^\n，。]{1,40})",
            r"(?:名为|叫做)\s*[「《]?([^\n」》]{1,40})",
        ]
        names: List[str] = []
        for p in patterns:
            for m in re.finditer(p, text):
                name = m.group(1).strip()
                if name and name not in names:
                    names.append(name)
        if not names:
            return ToolResult.text("未能识别剧名", details={"names": []})
        return ToolResult.text(
            "识别到的剧名：\n" + "\n".join(f"- {n}" for n in names[:10]),
            details={"names": names[:10]},
        )

    return ToolDefinition(
        name="extract_series_name",
        label="剧名提取",
        description="从文本中智能识别并提取短剧/剧名。",
        parameters={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
        execute=execute,
        category=ToolCategory.EXTERNAL,
        tags=["external", "extract", "was_agent:series_name_extractor"],
    )


def _tool_extract_series_info() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        text = params.get("text") or ""
        if not text:
            return ToolResult.fail("text 必填")
        info: Dict[str, Any] = {"raw_length": len(text)}
        title_m = re.search(r"[《「]([^》」]{1,40})[》」]", text)
        if title_m:
            info["title"] = title_m.group(1)
        ep_m = re.search(r"(?:共|总计)?\s*(\d{1,3})\s*集", text)
        if ep_m:
            info["episodes"] = int(ep_m.group(1))
        genre_m = re.search(r"(都市|甜宠|复仇|悬疑|穿越|重生|豪门|虐恋|爽文)", text)
        if genre_m:
            info["genre_hint"] = genre_m.group(1)
        lines = [f"{k}: {v}" for k, v in info.items()]
        return ToolResult.text("剧集信息提取：\n" + "\n".join(lines), details=info)

    return ToolDefinition(
        name="extract_series_info",
        label="剧集信息提取",
        description="从文本中提取剧名、集数、类型等结构化剧集信息。",
        parameters={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
        execute=execute,
        category=ToolCategory.EXTERNAL,
        tags=["external", "extract", "was_agent:series_info"],
    )


def _tool_format_output() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        text = params.get("text") or ""
        style = (params.get("style") or "markdown").lower()
        if not text:
            return ToolResult.fail("text 必填")
        cleaned = text.strip()
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        if style == "plain":
            cleaned = re.sub(r"[#>*`]+", "", cleaned)
        elif style == "script":
            # 简单剧本块标记规整
            cleaned = re.sub(r"(?m)^(场景|SCENE)\s*[:：]?", r"【场景】", cleaned)
        return ToolResult.text(cleaned, details={"style": style, "chars": len(cleaned)})

    return ToolDefinition(
        name="format_output",
        label="输出格式化",
        description="格式化 AI 输出为 markdown / plain / script，确保结构规范。",
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "style": {"type": "string", "enum": ["markdown", "plain", "script"], "default": "markdown"},
            },
            "required": ["text"],
        },
        execute=execute,
        category=ToolCategory.EXTERNAL,
        tags=["external", "format", "was_agent:output_formatter"],
    )


def _tool_generate_document() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        title = params.get("title") or "未命名文档"
        body = params.get("body") or ""
        doc_type = params.get("doc_type") or "script"
        header = {
            "script": "# 剧本文档",
            "outline": "# 大纲文档",
            "bible": "# 设定文档",
            "report": "# 评估报告",
        }.get(doc_type, "# 文档")
        md = f"{header}\n\n## {title}\n\n{body.strip()}\n"
        # 若有 drama_id，可写入 exports（可选）
        saved = None
        ctx = ctx or ToolContext()
        if ctx.drama_id and params.get("save"):
            try:
                from .sandbox import PathSandbox

                sb = PathSandbox(ctx.workspace_root, drama_id=ctx.drama_id)
                path = sb.resolve(f"projects/{ctx.drama_id}/exports/{doc_type}_{title[:20]}.md", write=True)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(md, encoding="utf-8")
                saved = str(path)
            except Exception as e:
                return ToolResult.text(md, details={"saved": False, "error": str(e)})
        return ToolResult.text(md, details={"doc_type": doc_type, "saved": saved})

    return ToolDefinition(
        name="generate_document",
        label="文档生成器",
        description="将标题与正文组装为标准化剧本文档（可可选保存到作品 exports）。",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "body": {"type": "string"},
                "doc_type": {
                    "type": "string",
                    "enum": ["script", "outline", "bible", "report"],
                    "default": "script",
                },
                "save": {"type": "boolean", "default": False},
            },
            "required": ["title", "body"],
        },
        execute=execute,
        category=ToolCategory.EXTERNAL,
        dangerous=True,
        tags=["external", "document", "was_agent:document_generator"],
    )


def _tool_file_reference() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        path = params.get("path") or ""
        if not path:
            return ToolResult.fail("path 必填")
        from .sandbox import PathSandbox

        ctx = ctx or ToolContext()
        sb = PathSandbox(ctx.workspace_root, drama_id=ctx.drama_id)
        try:
            fp = sb.resolve(path, write=False)
        except Exception as e:
            return ToolResult.fail(str(e))
        if not fp.exists() or not fp.is_file():
            return ToolResult.fail("文件不存在")
        max_chars = int(params.get("max_chars") or 12000)
        text = fp.read_text(encoding="utf-8", errors="ignore")
        truncated = len(text) > max_chars
        body = text[:max_chars]
        return ToolResult.text(
            f"引用文件: {path}\n\n{body}" + ("\n\n…(已截断)" if truncated else ""),
            details={"path": path, "chars": len(text), "truncated": truncated},
        )

    return ToolDefinition(
        name="file_reference",
        label="文件引用解析",
        description="在沙箱内解析并引用外部/项目文件内容，供专家上下文使用。",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "max_chars": {"type": "integer", "default": 12000},
            },
            "required": ["path"],
        },
        execute=execute,
        category=ToolCategory.EXTERNAL,
        requires_sandbox=True,
        tags=["external", "fs", "was_agent:file_reference"],
    )


def _tool_memory_search() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        drama_id = _resolve_drama_id(ctx, params)
        query = (params.get("query") or "").strip()
        if not drama_id:
            return ToolResult.fail("drama_id 必填（作品级记忆隔离）")
        try:
            from utils.agent_memory import get_agent_memory_service

            svc = get_agent_memory_service()
            layer = (params.get("layer") or "all").lower()
            parts = []
            if layer in ("all", "episodic"):
                eps = svc.search_episodes(drama_id, query, top_k=int(params.get("top_k") or 4))
                if eps:
                    parts.append("### 情节记忆")
                    for e in eps:
                        parts.append(
                            f"- [{e.get('outcome')}] {e.get('task_description','')[:100]} "
                            f"| {e.get('resolution') or e.get('approach') or ''}"[:160]
                        )
            if layer in ("all", "semantic"):
                facts = svc.search_facts(drama_id, query, top_k=int(params.get("top_k") or 8))
                if facts:
                    parts.append("### 语义事实")
                    for f in facts:
                        parts.append(
                            f"- {f.get('entity_type')}:{f.get('entity_id')} "
                            f"{f.get('predicate')}={f.get('value')}"
                        )
            if layer in ("all", "rules"):
                rules = svc.get_rules(drama_id)[:800]
                if rules.strip():
                    parts.append("### 规则摘录\n" + rules)
            return ToolResult.text(
                "\n".join(parts) if parts else "无命中记忆",
                details={"drama_id": drama_id, "query": query, "layer": layer},
            )
        except Exception as e:
            return ToolResult.fail(str(e))

    return ToolDefinition(
        name="memory_search",
        label="记忆检索",
        description="在作品记忆中检索规则/情节/语义事实。开写或决策前应调用，避免重复踩坑。",
        parameters={
            "type": "object",
            "properties": {
                "drama_id": {"type": "string"},
                "query": {"type": "string"},
                "layer": {
                    "type": "string",
                    "enum": ["all", "episodic", "semantic", "rules"],
                    "default": "all",
                },
                "top_k": {"type": "integer", "default": 5},
            },
            "required": ["query"],
        },
        execute=execute,
        category=ToolCategory.EXTERNAL,
        tags=["memory", "external"],
    )


def _tool_memory_write_fact() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        drama_id = _resolve_drama_id(ctx, params)
        if not drama_id:
            return ToolResult.fail("drama_id 必填")
        try:
            from utils.agent_memory import get_agent_memory_service

            fact = get_agent_memory_service().upsert_fact(
                drama_id=drama_id,
                entity_type=params["entity_type"],
                entity_id=params["entity_id"],
                predicate=params["predicate"],
                value=params["value"],
                confidence=params.get("confidence") or "fact",
                user_id=(ctx.user_id if ctx else None),
                provenance={
                    "source": "tool",
                    "agent_id": ctx.agent_id if ctx else None,
                    "tool_call_id": tool_call_id,
                },
                pinned=bool(params.get("pinned")),
            )
            return ToolResult.text(
                f"已写入事实 {fact['entity_type']}:{fact['entity_id']} "
                f"{fact['predicate']}={fact['value']}",
                details=fact,
            )
        except Exception as e:
            return ToolResult.fail(str(e))

    return ToolDefinition(
        name="memory_write_fact",
        label="写入语义事实",
        description="将耐久事实写入作品语义记忆（本体校验）。用于人设、悬念、世界不变量。",
        parameters={
            "type": "object",
            "properties": {
                "drama_id": {"type": "string"},
                "entity_type": {
                    "type": "string",
                    "enum": [
                        "character",
                        "episode",
                        "plot_thread",
                        "world_rule",
                        "style",
                        "decision",
                        "platform",
                    ],
                },
                "entity_id": {"type": "string"},
                "predicate": {"type": "string"},
                "value": {"type": "string"},
                "confidence": {
                    "type": "string",
                    "enum": ["fact", "inference", "preference", "hypothesis"],
                    "default": "fact",
                },
                "pinned": {"type": "boolean", "default": False},
            },
            "required": ["entity_type", "entity_id", "predicate", "value"],
        },
        execute=execute,
        category=ToolCategory.EXTERNAL,
        dangerous=True,
        tags=["memory", "external"],
    )


def _tool_memory_read_slice() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        drama_id = _resolve_drama_id(ctx, params)
        if not drama_id:
            return ToolResult.fail("drama_id 必填")
        try:
            from utils.agent_memory import get_agent_memory_service

            data = get_agent_memory_service().read_memory_slice(
                drama_id,
                relative_path=params["path"],
                offset=int(params.get("offset") or 0),
                length=int(params.get("length") or 2000),
            )
            return ToolResult.text(data.get("content") or "", details=data)
        except Exception as e:
            return ToolResult.fail(str(e))

    return ToolDefinition(
        name="memory_read_slice",
        label="局部读取记忆文件",
        description="按路径局部读取 topics/evidence 等历史文件，不全量灌进上下文。",
        parameters={
            "type": "object",
            "properties": {
                "drama_id": {"type": "string"},
                "path": {"type": "string", "description": "相对 memory/ 路径，如 topics/arc.md"},
                "offset": {"type": "integer", "default": 0},
                "length": {"type": "integer", "default": 2000},
            },
            "required": ["path"],
        },
        execute=execute,
        category=ToolCategory.EXTERNAL,
        tags=["memory", "external"],
    )


def _tool_memory_record_episode() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        try:
            from utils.agent_memory import get_agent_memory_service

            ep = get_agent_memory_service().record_agent_turn(
                user_id=(ctx.user_id if ctx else None) or params.get("user_id") or "default_user",
                agent_id=(ctx.agent_id if ctx else None) or params.get("agent_id") or "unknown",
                task_description=params["task_description"],
                drama_id=params.get("drama_id") or (ctx.drama_id if ctx else None),
                session_id=(ctx.session_id if ctx else None) or params.get("session_id"),
                outcome=params.get("outcome") or "success",
                approach=params.get("approach") or "",
                resolution=params.get("resolution") or "",
                errors=params.get("errors") or [],
                key_decisions=params.get("key_decisions") or [],
                tags=params.get("tags") or [],
            )
            return ToolResult.text(f"已记录情节 {ep.episode_id}", details=ep.to_dict())
        except Exception as e:
            return ToolResult.fail(str(e))

    return ToolDefinition(
        name="memory_record_episode",
        label="记录情节记忆",
        description="把本轮任务过程写入 episodic memory（recall 原料）。成功路径可后续晋升 skill。",
        parameters={
            "type": "object",
            "properties": {
                "drama_id": {"type": "string"},
                "task_description": {"type": "string"},
                "outcome": {
                    "type": "string",
                    "enum": ["success", "failure", "partial", "cancelled"],
                    "default": "success",
                },
                "approach": {"type": "string"},
                "resolution": {"type": "string"},
                "key_decisions": {"type": "array", "items": {"type": "string"}},
                "errors": {"type": "array", "items": {"type": "string"}},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["task_description"],
        },
        execute=execute,
        category=ToolCategory.EXTERNAL,
        tags=["memory", "external"],
    )


def _tool_memory_reflect() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        drama_id = _resolve_drama_id(ctx, params)
        if not drama_id:
            return ToolResult.fail("drama_id 必填")
        try:
            from utils.agent_memory import get_agent_memory_service

            svc = get_agent_memory_service()
            if params.get("episode_id"):
                ref = svc.reflect_on_episode(
                    drama_id,
                    params["episode_id"],
                    user_id=(ctx.user_id if ctx else None),
                )
            else:
                ref = svc.record_reflection(
                    drama_id=drama_id,
                    user_id=(ctx.user_id if ctx else None) or "default_user",
                    kind=params.get("kind") or "partial",
                    summary=params.get("summary") or "",
                    episode_id=params.get("episode_id"),
                    why=params.get("why") or [],
                    next_action=params.get("next_action") or "",
                )
            if not ref:
                return ToolResult.fail("无法生成反思")
            return ToolResult.text(ref.get("summary") or "已记录反思", details=ref)
        except Exception as e:
            return ToolResult.fail(str(e))

    return ToolDefinition(
        name="memory_reflect",
        label="反思成败",
        description="对情节做 reflection：总结为什么成功/失败，并绑定原始 episode。",
        parameters={
            "type": "object",
            "properties": {
                "drama_id": {"type": "string"},
                "episode_id": {"type": "string"},
                "kind": {"type": "string", "enum": ["success", "failure", "partial"]},
                "summary": {"type": "string"},
                "why": {"type": "array", "items": {"type": "string"}},
                "next_action": {"type": "string"},
            },
            "required": [],
        },
        execute=execute,
        category=ToolCategory.EXTERNAL,
        tags=["memory", "external"],
    )


def _tool_memory_promote_skill() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        drama_id = _resolve_drama_id(ctx, params)
        if not drama_id:
            return ToolResult.fail("drama_id 必填")
        try:
            from utils.agent_memory import get_agent_memory_service

            skill = get_agent_memory_service().promote_skill_from_episodes(
                drama_id,
                name=params["name"],
                trigger=params["trigger"],
                min_success=int(params.get("min_success") or 3),
            )
            if not skill:
                return ToolResult.fail("成功次数不足，未晋升")
            return ToolResult.text(f"已晋升技能 {skill['name']}", details=skill)
        except Exception as e:
            return ToolResult.fail(str(e))

    return ToolDefinition(
        name="memory_promote_skill",
        label="晋升程序技能",
        description="把重复成功的路径沉淀为 procedural memory（可复用步骤）。",
        parameters={
            "type": "object",
            "properties": {
                "drama_id": {"type": "string"},
                "name": {"type": "string"},
                "trigger": {"type": "string"},
                "min_success": {"type": "integer", "default": 3},
            },
            "required": ["name", "trigger"],
        },
        execute=execute,
        category=ToolCategory.EXTERNAL,
        dangerous=True,
        tags=["memory", "external"],
    )


def _tool_memory_forget() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        drama_id = _resolve_drama_id(ctx, params)
        if not drama_id:
            return ToolResult.fail("drama_id 必填")
        try:
            from utils.agent_memory import get_agent_memory_service

            data = get_agent_memory_service().run_forgetting(drama_id)
            return ToolResult.text(
                f"遗忘完成：归档 {data.get('archived_episodes')} · 过期 {data.get('expired_facts')} · "
                f"矛盾 {data.get('flagged_contradictions')}",
                details=data,
            )
        except Exception as e:
            return ToolResult.fail(str(e))

    return ToolDefinition(
        name="memory_forget",
        label="运行遗忘引擎",
        description="TTL 归档情节、过期事实、标记矛盾。治理用，非每轮调用。",
        parameters={
            "type": "object",
            "properties": {"drama_id": {"type": "string"}},
            "required": [],
        },
        execute=execute,
        category=ToolCategory.EXTERNAL,
        dangerous=True,
        tags=["memory", "external"],
    )


def _tool_memory_dream() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        drama_id = _resolve_drama_id(ctx, params)
        if not drama_id:
            return ToolResult.fail("drama_id 必填")
        try:
            from utils.agent_memory import get_agent_memory_service

            data = get_agent_memory_service().run_dream(
                drama_id,
                user_id=(ctx.user_id if ctx else None),
                auto_promote=bool(params.get("auto_promote", True)),
                compress_resident=bool(params.get("compress_resident", True)),
            )
            return ToolResult.text(
                f"Dreaming 完成：教训 {data.get('lessons_written')} · 反思 {data.get('reflections')} · "
                f"晋升 {len(data.get('skills_promoted') or [])}",
                details=data,
            )
        except Exception as e:
            return ToolResult.fail(str(e))

    return ToolDefinition(
        name="memory_dream",
        label="离线做梦整理",
        description="空闲时整理记忆：遗忘、反思沉淀、压缩 MEMORY、晋升技能、重建向量。勿在每轮对话滥用。",
        parameters={
            "type": "object",
            "properties": {
                "drama_id": {"type": "string"},
                "auto_promote": {"type": "boolean", "default": True},
                "compress_resident": {"type": "boolean", "default": True},
            },
            "required": [],
        },
        execute=execute,
        category=ToolCategory.EXTERNAL,
        dangerous=True,
        tags=["memory", "external"],
    )


def _tool_memory_delete() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        drama_id = _resolve_drama_id(ctx, params)
        if not drama_id:
            return ToolResult.fail("drama_id 必填")
        layer = (params.get("layer") or "").lower()
        target_id = params.get("target_id") or ""
        if not target_id:
            return ToolResult.fail("target_id 必填")
        try:
            from utils.agent_memory import get_agent_memory_service

            svc = get_agent_memory_service()
            uid = ctx.user_id if ctx else None
            ok = False
            if layer == "semantic":
                ok = svc.delete_fact(drama_id, target_id, user_id=uid)
            elif layer == "episodic":
                ok = svc.soft_delete_episode(drama_id, target_id, user_id=uid)
            elif layer == "procedural":
                ok = svc.delete_skill(drama_id, target_id, user_id=uid)
            else:
                return ToolResult.fail("layer 须为 semantic|episodic|procedural")
            return ToolResult.text("已删除" if ok else "未找到", details={"ok": ok})
        except Exception as e:
            return ToolResult.fail(str(e))

    return ToolDefinition(
        name="memory_delete",
        label="删除记忆",
        description="删除/归档事实、情节或技能（写审计日志，可追溯）。",
        parameters={
            "type": "object",
            "properties": {
                "drama_id": {"type": "string"},
                "layer": {"type": "string", "enum": ["semantic", "episodic", "procedural"]},
                "target_id": {"type": "string"},
            },
            "required": ["layer", "target_id"],
        },
        execute=execute,
        category=ToolCategory.EXTERNAL,
        dangerous=True,
        tags=["memory", "external"],
    )


def _tool_memory_write_resident() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        try:
            from utils.agent_memory import get_agent_memory_service

            svc = get_agent_memory_service()
            target = (params.get("target") or "drama").lower()
            content = params.get("content") or ""
            if target == "user":
                # 用户常驻画像：只用绑定用户，禁止 params 越权写任意用户
                uid = getattr(ctx, "user_id", None) if ctx else None
                if not uid:
                    return ToolResult.fail("user_id 必填（用户常驻画像需绑定用户）")
                svc.set_user_resident(uid, content, actor=ctx.agent_id if ctx else None)
            else:
                drama_id = _resolve_drama_id(ctx, params)
                if not drama_id:
                    return ToolResult.fail("drama_id 必填")
                svc.set_drama_resident(
                    drama_id,
                    content,
                    actor=ctx.agent_id if ctx else None,
                    user_id=ctx.user_id if ctx else None,
                )
            return ToolResult.text("常驻记忆已更新（已过注入扫描与长度校验）")
        except Exception as e:
            return ToolResult.fail(str(e))

    return ToolDefinition(
        name="memory_write_resident",
        label="写常驻记忆",
        description="更新 USER.md / MEMORY.md。只写短硬不变量；有注入扫描与字数上限。",
        parameters={
            "type": "object",
            "properties": {
                "target": {"type": "string", "enum": ["user", "drama"], "default": "drama"},
                "drama_id": {"type": "string"},
                "user_id": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["content"],
        },
        execute=execute,
        category=ToolCategory.EXTERNAL,
        dangerous=True,
        tags=["memory", "external"],
    )


def get_external_tools() -> List[ToolDefinition]:
    return [
        _tool_web_search(),
        _tool_web_fetch(),
        _tool_knowledge_query(),
        _tool_text_split(),
        _tool_text_truncate(),
        _tool_extract_series_name(),
        _tool_extract_series_info(),
        _tool_format_output(),
        _tool_generate_document(),
        _tool_file_reference(),
        _tool_memory_search(),
        _tool_memory_write_fact(),
        _tool_memory_read_slice(),
        _tool_memory_record_episode(),
        _tool_memory_reflect(),
        _tool_memory_promote_skill(),
        _tool_memory_forget(),
        _tool_memory_dream(),
        _tool_memory_delete(),
        _tool_memory_write_resident(),
    ]
