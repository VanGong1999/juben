"""共享作品上下文 — sections 裁剪、焦点集注入、文件索引单测"""

from __future__ import annotations

import asyncio

from utils.drama_context import (
    build_drama_context_block,
    context_sections_for,
    extract_focus_episode,
)


def test_context_sections_mapping():
    assert context_sections_for("creation") is None  # 创作需要全部
    assert context_sections_for("character") == frozenset(
        {"title", "genre", "world", "characters", "outline"}
    )
    # 故事/大纲必须看见人物，避免杜撰
    assert "characters" in (context_sections_for("story") or set())
    assert "outline" in (context_sections_for("story") or set())
    assert context_sections_for("planning") == frozenset(
        {"title", "genre", "description", "characters", "outline"}
    )
    assert "episodes" in (context_sections_for("evaluation") or set())
    assert "characters" in (context_sections_for("evaluation") or set())
    assert context_sections_for(None) is None
    assert context_sections_for("unknown_category") is None


def test_extract_focus_episode():
    assert extract_focus_episode("评估第1集") == 1
    assert extract_focus_episode("请评估第 12 集可播性") == 12
    assert extract_focus_episode("@drama[episode:3] 帮我看看") == 3
    assert extract_focus_episode("随便聊聊") is None


def _fake_manager(drama, episodes_content=None):
    episodes_content = episodes_content or {}

    class _M:
        async def get_drama(self, drama_id):
            return drama

        async def get_episode(self, drama_id, n):
            body = episodes_content.get(n, "")
            return {
                "number": n,
                "title": f"第{n}集",
                "status": "done" if body else "draft",
                "content": body,
                "word_count": len(body),
            }

        async def list_artifacts(self, drama_id, limit=12):
            return []

    return _M()


def test_build_context_trims_by_sections(monkeypatch):
    drama = {
        "title": "测试剧",
        "genre": "都市",
        "description": "一句话简介",
        "total_episodes": 80,
        "completed_episodes": 0,
        "bible": {"world": "世界观" * 120, "characters": "人物" * 120},
        "outline": "大纲" * 120,
        "episodes": [],
    }
    monkeypatch.setattr("utils.drama_manager.get_drama_manager", lambda: _fake_manager(drama))

    full = asyncio.run(build_drama_context_block("d1"))
    planning = asyncio.run(
        build_drama_context_block("d1", sections=context_sections_for("planning"))
    )
    character = asyncio.run(
        build_drama_context_block("d1", sections=context_sections_for("character"))
    )
    creation = asyncio.run(
        build_drama_context_block("d1", sections=context_sections_for("creation"))
    )
    story = asyncio.run(
        build_drama_context_block("d1", sections=context_sections_for("story"))
    )

    assert "世界观" in full and "人物小传" in full and "故事大纲" in full
    assert "作品文件索引" in full
    # 策划：有大纲与人物，无世界观全文
    assert "故事大纲" in planning and "人物小传" in planning
    assert "世界观/知识设定" not in planning
    # 人物：留世界观/人物/大纲
    assert "世界观" in character and "人物小传" in character
    # 创作：全部
    assert "世界观" in creation and "人物小传" in creation and "故事大纲" in creation
    # 故事类必须含人物
    assert "人物小传" in story and "故事大纲" in story
    assert len(planning) < len(full)


def test_focus_episode_injected_not_only_recent(monkeypatch):
    """评估第1集时必须注入第1集正文，即使已写到第5集。"""
    drama = {
        "title": "测试剧",
        "genre": "都市",
        "description": "简介",
        "total_episodes": 80,
        "completed_episodes": 5,
        "bible": {"world": "世界", "characters": "主角甲"},
        "outline": "很长的大纲" * 200,
        "episodes": [
            {"number": n, "title": f"第{n}集", "status": "done", "word_count": 500}
            for n in range(1, 6)
        ],
    }
    bodies = {n: f"第{n}集完整正文内容UNIQUE_EP_{n}_" + ("字" * 400) for n in range(1, 6)}
    monkeypatch.setattr(
        "utils.drama_manager.get_drama_manager",
        lambda: _fake_manager(drama, bodies),
    )

    block = asyncio.run(
        build_drama_context_block(
            "d1",
            sections=context_sections_for("evaluation"),
            query="评估第1集可播性",
            budget_chars=3500,  # 旧逻辑会被大纲挤掉
        )
    )
    assert "UNIQUE_EP_1_" in block
    assert "第1集正文" in block
