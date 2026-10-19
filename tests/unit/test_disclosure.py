"""渐进式披露 / Deferred Tool Loading 单测"""

from __future__ import annotations

import pytest


def test_prepare_disclosure_keeps_core_small():
    from utils.agent_tools.registry import get_agent_tool_registry
    from utils.agent_infra.disclosure import prepare_disclosure, META_TOOLS

    registry = get_agent_tool_registry()
    bundle = prepare_disclosure(
        registry,
        include_meta=True,
        include_orchestration=True,
        include_skills_catalog=True,
        include_agents_catalog=True,
        allow_write=False,
    )
    names = bundle.tool_names()
    # 核心 + 元工具常驻
    assert "tool_search" in names
    assert "skill_search" in names
    assert "read" in names
    assert "ls" in names
    # 低频外部工具不应默认完整加载
    assert "web_search" not in names
    assert "knowledge_query" not in names
    assert "generate_document" not in names
    # 名录里应提到 deferred 工具
    assert "web_search" in bundle.prompt_append or "Deferred Tools" in bundle.prompt_append
    assert "Deferred Skills" in bundle.prompt_append
    assert len(names) < 30  # 远小于全量 50+
    for m in META_TOOLS:
        assert m in names


def test_tool_search_activates_into_tools_list():
    import asyncio
    import utils.agent_tools.registry as reg_mod
    from utils.agent_tools.types import ToolContext
    from utils.agent_infra.disclosure import activate_tools_from_result, prepare_disclosure

    # 强制重新注册，确保 meta tools 在单例里
    reg_mod._registry = None
    reg_mod._harness = None
    registry = reg_mod.get_agent_tool_registry()
    assert registry.get("tool_search") is not None

    bundle = prepare_disclosure(registry, include_meta=True, allow_write=False)
    tools = list(bundle.tools)
    assert "web_search" not in bundle.tool_names()

    async def _run():
        harness = reg_mod.get_tool_harness()
        ctx = ToolContext(metadata={"activated_tools": []})
        packed = await harness.execute(
            "tool_search",
            {"names": ["web_search"]},
            ctx=ctx,
            skip_egress=True,
        )
        assert packed.get("success"), packed.get("error")
        activated = set(ctx.metadata.get("activated_tools") or [])
        merged = activate_tools_from_result(
            tools,
            packed,
            registry,
            activated=activated,
            allow_write=False,
        )
        merged_names = [
            (t.get("function") or {}).get("name") for t in merged
        ]
        assert "web_search" in merged_names
        assert "web_search" in activated

    asyncio.run(_run())


def test_skills_default_catalog_not_full_body():
    from utils.skill_loader import build_skills_prompt, list_skills

    skills = list_skills()
    if not skills:
        pytest.skip("no skills md")
    catalog = build_skills_prompt(mode="catalog", max_chars=4000)
    assert "Deferred Skills" in catalog or "`" in catalog
    # 全文模式才应含大段 checklist 标题
    full = build_skills_prompt(mode="full", include_body=True, max_chars=20000)
    assert len(full) > len(catalog)
