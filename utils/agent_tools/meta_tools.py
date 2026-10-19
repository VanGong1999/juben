"""
元工具：tool_search / skill_search / load_skill / agent_search

渐进式披露入口——自身 always_load=True，用于把低频能力「搜出来再激活」。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .types import ToolCategory, ToolContext, ToolDefinition, ToolResult, ToolUpdateCallback


def _tool_search() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        from utils.agent_infra.disclosure import match_tools
        from utils.agent_tools.registry import get_agent_tool_registry

        registry = get_agent_tool_registry()
        query = str(params.get("query") or "").strip()
        names = params.get("names")
        if isinstance(names, str):
            names = [n.strip() for n in names.replace(";", ",").split(",") if n.strip()]
        limit = int(params.get("limit") or 8)

        hits = match_tools(registry, query=query, names=names, limit=limit)
        if not hits:
            return ToolResult.text(
                "未找到匹配工具。请换关键词，或检查 Deferred Tools 名录中的准确工具名。",
                details={"activate_tools": [], "matches": []},
            )

        # 记录到 ctx，便于 session 级复用
        ctx = ctx or ToolContext()
        activated = set(ctx.metadata.get("activated_tools") or [])
        schemas: List[Dict[str, Any]] = []
        lines: List[str] = ["已找到并激活以下工具（本轮后续可直接调用）："]
        for t in hits:
            activated.add(t.name)
            schemas.append(t.openai_schema())
            lines.append(f"### `{t.name}` — {t.label}")
            lines.append(t.description or "")
            lines.append("parameters schema:")
            lines.append(json.dumps(t.parameters or {}, ensure_ascii=False, indent=2))
            lines.append("")

        ctx.metadata["activated_tools"] = sorted(activated)

        if on_update:
            await on_update(
                {
                    "status": "done",
                    "phase": "tool_search",
                    "activate_tools": [t.name for t in hits],
                }
            )

        return ToolResult.text(
            "\n".join(lines),
            details={
                "activate_tools": [t.name for t in hits],
                "matches": [
                    {"name": t.name, "label": t.label, "always_load": t.always_load}
                    for t in hits
                ],
                "schemas": schemas,
            },
        )

    return ToolDefinition(
        name="tool_search",
        label="搜索工具",
        description=(
            "搜索并激活低频工具的完整定义（Deferred Tool Loading）。"
            "当 Deferred Tools 名录里有你需要的工具时，先调用本工具，"
            "再在后续步骤使用该工具。可按 names 精确激活，或按 query 关键词搜索。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "关键词，如 web、memory、document、series",
                },
                "names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "精确工具名列表，如 [\"web_search\",\"knowledge_query\"]",
                },
                "limit": {"type": "integer", "default": 8, "description": "最多返回条数"},
            },
            "required": [],
        },
        execute=execute,
        category=ToolCategory.PREBUILT,
        always_load=True,
        tags=["meta", "disclosure", "search"],
    )


def _skill_search() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        from utils.skill_loader import list_skills, get_skill

        query = str(params.get("query") or "").strip().lower()
        skill_id = str(params.get("skill_id") or "").strip()
        include_body = bool(params.get("include_body", True))
        limit = int(params.get("limit") or 5)

        if skill_id:
            s = get_skill(skill_id)
            hits = [s] if s else []
        else:
            skills = [s for s in list_skills() if s.get("enabled")]
            if query:
                tokens = [t for t in query.replace(",", " ").split() if t]
                scored = []
                for s in skills:
                    blob = f"{s.get('id')} {s.get('name')} {s.get('summary')} {s.get('description')} {s.get('category')}".lower()
                    score = sum(1 for t in tokens if t in blob)
                    if score:
                        scored.append((score, s))
                scored.sort(key=lambda x: -x[0])
                hits = [s for _, s in scored[:limit]]
            else:
                hits = skills[:limit]

        if not hits:
            return ToolResult.text("未找到匹配 skill。请查看 Deferred Skills 名录中的 id。")

        ctx = ctx or ToolContext()
        loaded = set(ctx.metadata.get("activated_skills") or [])
        chunks: List[str] = []
        for s in hits:
            loaded.add(s["id"])
            chunks.append(f"### {s.get('name')} (`{s.get('id')}`)")
            chunks.append(s.get("summary") or s.get("description") or "")
            if include_body:
                body = (s.get("body") or "").strip()
                if body:
                    chunks.append(body)
            chunks.append("")
        ctx.metadata["activated_skills"] = sorted(loaded)

        return ToolResult.text(
            "\n".join(chunks),
            details={"activate_skills": [s["id"] for s in hits], "count": len(hits)},
        )

    return ToolDefinition(
        name="skill_search",
        label="搜索技能",
        description=(
            "按关键词搜索写作 Skills，并返回摘要或完整正文。"
            "Deferred Skills 名录只有名字时，用本工具加载 checklist。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "关键词，如 钩子、对白、反派"},
                "skill_id": {"type": "string", "description": "精确 skill id，如 cliffhanger"},
                "include_body": {"type": "boolean", "default": True},
                "limit": {"type": "integer", "default": 5},
            },
            "required": [],
        },
        execute=execute,
        category=ToolCategory.PREBUILT,
        always_load=True,
        tags=["meta", "disclosure", "skills"],
    )


def _load_skill() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        from utils.skill_loader import get_skill

        skill_id = str(params.get("skill_id") or "").strip()
        if not skill_id:
            return ToolResult.fail("skill_id 必填")
        s = get_skill(skill_id)
        if not s:
            return ToolResult.fail(f"skill 不存在: {skill_id}")

        ctx = ctx or ToolContext()
        loaded = set(ctx.metadata.get("activated_skills") or [])
        loaded.add(skill_id)
        ctx.metadata["activated_skills"] = sorted(loaded)

        body = (s.get("body") or "").strip()
        text = f"### {s.get('name')} (`{skill_id}`)\n{s.get('summary') or ''}\n\n{body}"
        return ToolResult.text(text, details={"activate_skills": [skill_id]})

    return ToolDefinition(
        name="load_skill",
        label="加载技能正文",
        description="按 skill_id 加载完整 Skill Markdown 正文（渐进式披露）。",
        parameters={
            "type": "object",
            "properties": {
                "skill_id": {"type": "string", "description": "如 cliffhanger / hook-3s / character-voice"},
            },
            "required": ["skill_id"],
        },
        execute=execute,
        category=ToolCategory.PREBUILT,
        always_load=True,
        tags=["meta", "disclosure", "skills"],
    )


def _agent_search() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        try:
            from config.agents import get_all_agents_config, get_agent_config
        except Exception as e:
            return ToolResult.fail(f"无法加载专家目录: {e}")

        query = str(params.get("query") or "").strip().lower()
        agent_id = str(params.get("agent_id") or "").strip()
        limit = int(params.get("limit") or 6)

        if agent_id:
            cfg = get_agent_config(agent_id)
            hits = [cfg] if cfg else []
        else:
            configs = get_all_agents_config(include_utility=False)
            if query:
                tokens = [t for t in query.replace(",", " ").split() if t]
                scored = []
                for c in configs:
                    blob = (
                        f"{c.get('id')} {c.get('display_name')} {c.get('description')} "
                        f"{' '.join(c.get('features') or [])} {c.get('category')}"
                    ).lower()
                    score = sum(1 for t in tokens if t in blob)
                    if score:
                        scored.append((score, c))
                scored.sort(key=lambda x: -x[0])
                hits = [c for _, c in scored[:limit]]
            else:
                hits = configs[:limit]

        if not hits:
            return ToolResult.text("未找到匹配专家。请查看 Deferred Agents 名录。")

        lines: List[str] = ["匹配专家："]
        for c in hits:
            lines.append(f"### `{c.get('id')}` — {c.get('display_name')}")
            lines.append(c.get("description") or "")
            feats = c.get("features") or []
            if feats:
                lines.append("能力: " + "、".join(feats[:6]))
            lines.append(f"示例输入: {c.get('input_example') or ''}")
            lines.append("")

        return ToolResult.text(
            "\n".join(lines),
            details={"agents": [c.get("id") for c in hits]},
        )

    return ToolDefinition(
        name="agent_search",
        label="搜索专家",
        description=(
            "搜索专家目录详情（渐进式披露）。"
            "名录只有 id/简介时，用本工具查看能力与示例；真正执行请用 spawn_subagent / transfer_to。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "关键词，如 评估、IP、情节点、人物"},
                "agent_id": {"type": "string", "description": "精确专家 id"},
                "limit": {"type": "integer", "default": 6},
            },
            "required": [],
        },
        execute=execute,
        category=ToolCategory.PREBUILT,
        always_load=True,
        tags=["meta", "disclosure", "agents"],
    )


def get_meta_tools() -> List[ToolDefinition]:
    return [
        _tool_search(),
        _skill_search(),
        _load_skill(),
        _agent_search(),
    ]
