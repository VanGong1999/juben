"""把 skills/*/SKILL.md 的详细内容沉淀为 LLM Wiki 页，丰富知识库 L2。

skills 目录里已是「可注入 checklist」的短剧创作技法（开场/卡点/情绪/人设/对白/
节奏/反派/爽点），但 LLM Wiki（data/knowledge/wiki）只有稀疏的种子页。
本脚本把二者打通：agent 通过 `wiki_read` 也能拿到与 skills 一致的结构化知识。

用法：venv/bin/python scripts/sync_skills_to_wiki.py
可重复执行（skills 更新后重跑即可），幂等覆盖同 slug 页。
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from utils.llm_wiki.store import LlmWikiStore, _parse_frontmatter  # noqa: E402

SKILLS_DIR = PROJECT_ROOT / "skills"

# 叙事概念类放 concepts/，其余技法放 craft/
_CONCEPT_SKILLS = {"emotion-first"}


def main() -> None:
    store = LlmWikiStore()
    count = 0
    for skill_md in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8")
        fm, body = _parse_frontmatter(text)
        skill_id = str(fm.get("id") or skill_md.parent.name)
        name = str(fm.get("name") or skill_id)
        summary = str(fm.get("summary") or fm.get("description") or name)
        category = "concepts" if skill_id in _CONCEPT_SKILLS else "craft"
        tags = [str(fm.get("category") or "craft")]
        store.write_wiki_page(
            category=category,
            slug=skill_id,
            title=name,
            summary=summary,
            body=body,
            tags=tags,
            sources=[],
            cache_tier="L2",
            rebuild_index=False,
        )
        count += 1
        print(f"[wiki] {category}/{skill_id}.md  <-  {skill_md.relative_to(PROJECT_ROOT)}")

    store.rebuild_index()
    stats = store.stats()
    print(f"\ndone: {count} skills -> wiki, 总计 wiki_pages={stats['wiki_pages']}")


if __name__ == "__main__":
    main()
