"""
渐进式披露（Progressive Disclosure）— Claude Code Deferred Tool Loading

研究结论：工具从 10→50，模型选型准确率约 90%→<50%。
策略：
  1. 核心工具（always_load）完整 schema 常驻 tools[]
  2. 低频工具只在 system 里放「名字 + 一行说明」名录
  3. 需要时先调 tool_search / skill_search / agent_search，再把完整定义激活进本轮 loop

同理：Skills / Agents 目录也只注入名录，正文/详情按需加载。
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# 几乎每轮都会用到的文件系统 / 时间工具
DEFAULT_CORE_TOOLS: tuple[str, ...] = (
    "read",
    "write",
    "edit",
    "ls",
    "grep",
    "find",
    "date",
)

# 元工具：搜索并激活低频能力（自身必须 always_load）
META_TOOLS: tuple[str, ...] = (
    "tool_search",
    "skill_search",
    "load_skill",
    "agent_search",
    "wiki_read",
    "wiki_search",
)

# Conductor 编排原语（会话级常驻）
ORCHESTRATION_CORE_TOOLS: tuple[str, ...] = (
    "spawn_subagent",
    "transfer_to",
    "compose_agents",
    "return_to_conductor",
)

WRITE_DANGEROUS = frozenset({"run_shell", "run_python", "write", "edit", "save_drama_part"})


@dataclass
class DisclosureBundle:
    """一次 Agent turn 的披露结果。"""

    tools: List[Dict[str, Any]]
    prompt_append: str
    core_names: List[str] = field(default_factory=list)
    deferred_names: List[str] = field(default_factory=list)
    activated: Set[str] = field(default_factory=set)

    def tool_names(self) -> List[str]:
        names: List[str] = []
        for t in self.tools:
            fn = t.get("function") or {}
            n = fn.get("name")
            if n:
                names.append(n)
        return names


def _tool_name_from_schema(schema: Dict[str, Any]) -> str:
    return str((schema.get("function") or {}).get("name") or "")


def mark_core_tools(registry: Any, names: Optional[List[str]] = None) -> None:
    """把指定工具标为 always_load（幂等）。"""
    names = names or list(DEFAULT_CORE_TOOLS) + list(META_TOOLS) + list(ORCHESTRATION_CORE_TOOLS)
    for name in names:
        tool = registry.get(name)
        if tool is not None:
            tool.always_load = True


def resolve_core_names(
    registry: Any,
    *,
    extra_core: Optional[List[str]] = None,
    include_meta: bool = True,
    include_orchestration: bool = False,
) -> List[str]:
    """决定本轮常驻完整 schema 的工具名。"""
    names: List[str] = []
    seen: Set[str] = set()

    def _add(n: str) -> None:
        if n and n not in seen and registry.get(n):
            seen.add(n)
            names.append(n)

    for n in DEFAULT_CORE_TOOLS:
        _add(n)
    # 注册表里标了 always_load 的也纳入
    for t in registry.list(enabled_only=True):
        if getattr(t, "always_load", False):
            _add(t.name)
    if include_meta:
        for n in META_TOOLS:
            _add(n)
    if include_orchestration:
        for n in ORCHESTRATION_CORE_TOOLS:
            _add(n)
    if extra_core:
        for n in extra_core:
            _add(n)
    return names


def build_tools_catalog(
    registry: Any,
    *,
    exclude: Optional[Set[str]] = None,
    pool: Optional[List[str]] = None,
    max_items: int = 80,
) -> str:
    """低频工具名录（不含完整 parameters）。"""
    exclude = exclude or set()
    lines: List[str] = []
    tools = registry.list(enabled_only=True)
    if pool is not None:
        allow = set(pool)
        tools = [t for t in tools if t.name in allow]
    for t in tools:
        if t.name in exclude:
            continue
        if getattr(t, "always_load", False) and t.name in exclude:
            continue
        lines.append(t.catalog_line())
        if len(lines) >= max_items:
            break
    if not lines:
        return ""
    return (
        "## Deferred Tools（名录）\n"
        "以下工具未加载完整参数定义。需要时先调用 `tool_search`（按名或关键词），"
        "拿到 schema 后再调用该工具。\n"
        + "\n".join(lines)
    )


def build_skills_catalog(*, enabled_only: bool = True, max_items: int = 40) -> str:
    from utils.skill_loader import list_skills

    skills = list_skills()
    if enabled_only:
        skills = [s for s in skills if s.get("enabled")]
    if not skills:
        return ""
    lines = [
        "## Deferred Skills（名录）",
        "写作规范仅列名称与摘要。需要完整 checklist 时调用 `skill_search` 或 `load_skill`。",
    ]
    for s in skills[:max_items]:
        summary = (s.get("summary") or s.get("description") or "").replace("\n", " ").strip()
        if len(summary) > 100:
            summary = summary[:97] + "…"
        lines.append(f"- `{s.get('id')}` — **{s.get('name')}**: {summary}")
    return "\n".join(lines)


def build_agents_catalog(
    *,
    include_utility: bool = False,
    max_items: int = 40,
    allowed_ids: Optional[List[str]] = None,
) -> str:
    try:
        from config.agents import get_all_agents_config
    except Exception:
        return ""

    configs = get_all_agents_config(include_utility=include_utility)
    if allowed_ids is not None:
        allow = set(allowed_ids)
        configs = [c for c in configs if c.get("id") in allow]
    # 去掉 auto 重复项旁的工具类噪音
    skip = {"auto", "minimal_tool_agent", "websearch", "knowledge"}
    lines = [
        "## Deferred Agents（名录）",
        "专家详情未全量注入。需要时调用 `agent_search`；执行任务用 `spawn_subagent` / `transfer_to`。",
    ]
    n = 0
    for c in configs:
        aid = c.get("id") or ""
        if aid in skip:
            continue
        if c.get("category") in ("utility", "tools") and not include_utility:
            continue
        desc = (c.get("description") or "").replace("\n", " ").strip()
        if len(desc) > 90:
            desc = desc[:87] + "…"
        lines.append(f"- `{aid}` — **{c.get('display_name') or aid}**: {desc}")
        n += 1
        if n >= max_items:
            break
    return "\n".join(lines) if n else ""


def build_wiki_index_block(*, max_chars: int = 6000) -> str:
    """L1：知识库 index.md，应常驻 system prompt。"""
    try:
        from utils.llm_wiki import build_wiki_index_prompt, ensure_wiki_bootstrapped

        ensure_wiki_bootstrapped()
        return build_wiki_index_prompt(max_chars=max_chars)
    except Exception as e:
        logger.debug("wiki index block soft-fail: %s", e)
        return ""


def prepare_disclosure(
    registry: Any,
    *,
    extra_core: Optional[List[str]] = None,
    candidate_pool: Optional[List[str]] = None,
    include_meta: bool = True,
    include_orchestration: bool = False,
    include_skills_catalog: bool = True,
    include_agents_catalog: bool = False,
    # 默认 False：L1 index 由 assemble_prompt_bundle 注入稳定前缀，避免塞进 system 后被 rules_chars 截断
    include_wiki_index: bool = False,
    allowed_agent_ids: Optional[List[str]] = None,
    allow_write: bool = False,
    activated: Optional[Set[str]] = None,
) -> DisclosureBundle:
    """
    组装本轮：常驻 tools schema + 名录 prompt + 已激活工具。

    candidate_pool: 若给定，名录与可激活范围限制在此集合（含 core）。
    activated: 上一轮 / 本 session 已 tool_search 激活的工具名。
    """
    mark_core_tools(registry)
    core = resolve_core_names(
        registry,
        extra_core=extra_core,
        include_meta=include_meta,
        include_orchestration=include_orchestration,
    )
    activated = set(activated or ())

    # 危险写工具：无 allow_write 时从 core 去掉
    if not allow_write:
        core = [n for n in core if n not in WRITE_DANGEROUS]
        activated = {n for n in activated if n not in WRITE_DANGEROUS}

    load_names = list(dict.fromkeys([*core, *sorted(activated)]))
    schemas = registry.openai_tools(names=load_names)

    # 名录：全库（或 pool）减去已完整加载的
    loaded = set(load_names)
    catalog = build_tools_catalog(registry, exclude=loaded, pool=candidate_pool)

    parts: List[str] = []
    if include_wiki_index:
        wiki_idx = build_wiki_index_block()
        if wiki_idx:
            parts.append(wiki_idx)
    if catalog:
        parts.append(catalog)
    if include_skills_catalog:
        sc = build_skills_catalog()
        if sc:
            parts.append(sc)
    if include_agents_catalog:
        ac = build_agents_catalog(allowed_ids=allowed_agent_ids)
        if ac:
            parts.append(ac)

    deferred: List[str] = []
    for t in registry.list(enabled_only=True):
        if t.name in loaded:
            continue
        if candidate_pool is not None and t.name not in candidate_pool:
            continue
        deferred.append(t.name)

    return DisclosureBundle(
        tools=schemas,
        prompt_append="\n\n".join(parts),
        core_names=core,
        deferred_names=deferred,
        activated=activated,
    )


def activate_tools_from_result(
    tools: List[Dict[str, Any]],
    packed: Dict[str, Any],
    registry: Any,
    *,
    activated: Optional[Set[str]] = None,
    allow_write: bool = False,
) -> List[Dict[str, Any]]:
    """
    若 tool_search 等返回 details.activate_tools，把完整 schema 并入本轮 tools[]。
    返回新的 tools 列表（已按 name 去重排序）。
    """
    activated = activated if activated is not None else set()
    details = {}
    raw = packed.get("result")
    if isinstance(raw, dict):
        details = raw.get("details") or {}
    to_add = details.get("activate_tools") or details.get("activated_tools") or []
    if not to_add:
        return tools

    existing = {_tool_name_from_schema(t) for t in tools}
    new_names: List[str] = []
    for name in to_add:
        name = str(name or "").strip()
        if not name or name in existing:
            continue
        if not allow_write and name in WRITE_DANGEROUS:
            continue
        if registry.get(name) is None:
            continue
        new_names.append(name)
        activated.add(name)
        existing.add(name)

    if not new_names:
        return tools

    added = registry.openai_tools(names=new_names)
    merged = list(tools) + list(added)
    try:
        from utils.agent_infra.prompt_cache import sort_tools_for_cache

        return sort_tools_for_cache(merged)
    except Exception:
        return merged


def match_tools(
    registry: Any,
    *,
    query: str = "",
    names: Optional[List[str]] = None,
    limit: int = 8,
) -> List[Any]:
    """按名字精确或关键词模糊匹配工具定义。"""
    tools = registry.list(enabled_only=True)
    hit: List[Any] = []
    if names:
        want = {str(n).strip() for n in names if n}
        for t in tools:
            if t.name in want:
                hit.append(t)
    q = (query or "").strip().lower()
    if q:
        tokens = [tok for tok in re.split(r"[\s,;/|]+", q) if tok]
        scored: List[tuple[int, Any]] = []
        for t in tools:
            blob = f"{t.name} {t.label} {t.description} {' '.join(t.tags or [])}".lower()
            score = sum(1 for tok in tokens if tok in blob)
            if score:
                scored.append((score, t))
        scored.sort(key=lambda x: (-x[0], x[1].name))
        for _, t in scored:
            if t not in hit:
                hit.append(t)
    return hit[:limit]
