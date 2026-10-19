"""LLM Wiki 三级缓存单测"""

from __future__ import annotations

from pathlib import Path


def test_wiki_three_tier(tmp_path: Path):
    from utils.llm_wiki.store import LlmWikiStore
    from utils.llm_wiki.bootstrap_seed import seed_if_empty
    from utils.llm_wiki.prompt import build_wiki_index_prompt

    store = LlmWikiStore(tmp_path / "knowledge")
    store.ensure_layout()
    assert seed_if_empty(store) is True

    index = store.read_index()
    assert "Wiki Index" in index
    assert "cliffhanger" in index or "集末" in index

    page = store.read_wiki_page("craft/cliffhanger.md")
    assert page["ok"]
    assert "付费" in page["content"] or "钩" in page["content"]
    assert page.get("sources")

    raw = store.read_raw(page["sources"][0])
    assert raw["ok"]
    assert len(raw["content"]) > 10

    prompt = build_wiki_index_prompt(root=tmp_path / "knowledge")
    assert "Knowledge Wiki Index" in prompt
    assert "wiki_read" in prompt


def test_wiki_tools_registered():
    import utils.agent_tools.registry as reg_mod

    reg_mod._registry = None
    reg_mod._harness = None
    registry = reg_mod.get_agent_tool_registry()
    assert registry.get("wiki_read") is not None
    assert registry.get("wiki_search") is not None
    assert registry.get("raw_read") is not None
    assert registry.get("wiki_ingest") is not None
    assert registry.get("wiki_read").always_load is True
    assert registry.get("raw_read").always_load is False
