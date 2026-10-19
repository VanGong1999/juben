"""文件图谱兜底 + 示例短剧数据"""

from __future__ import annotations

import asyncio
from pathlib import Path


def test_file_graph_seed_and_elements(tmp_path: Path):
    from utils.file_graph_store import FileGraphStore, DEMO_STORY_ID

    async def _run():
        store = FileGraphStore(tmp_path / "graph")
        await store.initialize()
        stories = await store.list_stories()
        assert any(s.get("story_id") == DEMO_STORY_ID for s in stories)

        els = await store.get_story_elements(DEMO_STORY_ID)
        assert len(els["characters"]) >= 4
        assert len(els["plot_nodes"]) >= 3
        assert len(els["relationships"]) >= 10
        assert any(n["type"] == "Character" and n["properties"]["name"] == "林晓" for n in els["nodes"])

        stats = await store.get_story_statistics(DEMO_STORY_ID)
        assert stats["character_count"] >= 4
        assert stats["plot_count"] >= 3

        queue = await store.list_review_queue_entries(DEMO_STORY_ID, status="pending")
        assert queue["total"] >= 1

        path = await store.find_shortest_path(DEMO_STORY_ID, "char_linxiao", "char_chenshuo")
        assert path

        backend = getattr(store, "backend", "file")
        assert backend == "file"

    asyncio.run(_run())


# get_graph_manager 回退逻辑见 utils/graph_manager.py；
# 本机 neo4j 驱动导入可能 segfault，故不在 CI 中强连 bolt。
