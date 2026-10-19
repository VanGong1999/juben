"""
共享作品上下文 — 单一事实源 + 动态发现（Dynamic Context Discovery）。

设计原则（对齐 Cursor / Anthropic 实践）：
1. 默认注入「薄指针」：文件索引 + 短摘要，而不是把全部产物塞进 prompt。
2. 用户点名某集 / `@drama[...]` 时，优先展开该目标全文（评估等无工具专家必须看得见）。
3. 其余内容由 agent 用 `list_drama_artifacts` / `read_drama_part` / `search_drama_content` 按需拉取。

数据一律来自 projects/{drama_id}/（drama.json + bible + outline + episodes）。
"""

from __future__ import annotations

import re
from typing import Optional

# 用户说「第 N 集」时解析焦点集
_FOCUS_EP_RE = re.compile(
    r"(?:第\s*(\d+)\s*集|@drama\[\s*episode\s*:\s*(\d+)\s*\]|episode[_\s#:/-]*(\d+))",
    re.IGNORECASE,
)


def _clip(text: str, n: int) -> str:
    text = (text or "").strip()
    if len(text) <= n:
        return text
    return text[: max(0, n - 12)] + "…[截断]"


def extract_focus_episode(text: str) -> Optional[int]:
    """从用户请求中解析焦点集号（第N集 / @drama[episode:N]）。"""
    if not text:
        return None
    m = _FOCUS_EP_RE.search(text)
    if not m:
        return None
    for g in m.groups():
        if g:
            try:
                n = int(g)
                return n if n > 0 else None
            except ValueError:
                continue
    return None


# agent category -> 需要的上下文部分。None = 全部（默认）。
# episodes：已写剧本正文（评估/分析类需要真实剧本；有焦点集时优先注入该集全文）。
CATEGORY_CONTEXT_SECTIONS: dict[str, Optional[frozenset[str]]] = {
    "creation": None,  # 创作：需要全部
    "character": frozenset({"title", "genre", "world", "characters", "outline"}),
    # 故事/大纲类必须看见已有人物，避免杜撰新人设
    "story": frozenset({"title", "genre", "characters", "outline", "world"}),
    "analysis": frozenset({"title", "genre", "characters", "outline", "episodes"}),
    "planning": frozenset({"title", "genre", "description", "characters", "outline"}),
    "evaluation": frozenset({"title", "genre", "description", "characters", "outline", "episodes"}),
    "workflow": frozenset({"title", "genre", "description", "characters", "outline"}),
}


def context_sections_for(category: Optional[str]) -> Optional[frozenset[str]]:
    """按 agent category 返回需要的上下文部分集合；未知/None 返回 None（全部）。"""
    if not category:
        return None
    return CATEGORY_CONTEXT_SECTIONS.get(category)


async def build_drama_artifact_catalog(drama_id: str, *, max_artifacts: int = 12) -> str:
    """薄指针索引：列出当前作品可读文件，供 agent 按需 read/grep。"""
    if not drama_id:
        return ""
    try:
        from utils.drama_manager import get_drama_manager

        mgr = get_drama_manager()
        drama = await mgr.get_drama(drama_id)
        if not drama:
            return ""

        lines: list[str] = ["【作品文件索引】（薄指针：需要细节时用 read_drama_part / search_drama_content）"]
        bible = drama.get("bible") or {}
        world = (bible.get("world") or "").strip()
        characters = (bible.get("characters") or "").strip()
        outline = (drama.get("outline") or "").strip()

        lines.append(
            f"- world（世界观）· {len(world)} 字 · {'有' if world else '空'} · target=world"
        )
        lines.append(
            f"- characters（人物小传）· {len(characters)} 字 · {'有' if characters else '空'} · target=characters"
        )
        lines.append(
            f"- outline（故事大纲）· {len(outline)} 字 · {'有' if outline else '空'} · target=outline"
        )

        episodes = drama.get("episodes") or []
        done = [e for e in episodes if e.get("status") == "done"]
        if done:
            ep_bits = [
                f"ep_{int(e.get('number') or 0):03d}.md"
                f"（第{e.get('number')}集·{e.get('word_count') or 0}字·{e.get('title') or ''}）"
                for e in done
            ]
            lines.append(f"- episodes/ 已写 {len(done)} 集：{', '.join(ep_bits)}")
            lines.append("  → 读取：read_drama_part(target=episode, episode_number=N)")
        else:
            lines.append("- episodes/ 尚无已写分集")

        try:
            arts = await mgr.list_artifacts(drama_id, limit=max_artifacts)
            if arts:
                art_bits = [
                    f"{a.get('kind')}:{a.get('title') or a.get('id')}（{a.get('word_count') or 0}字）"
                    for a in arts[:max_artifacts]
                ]
                lines.append(f"- agent_outputs/ 最近产物：{'; '.join(art_bits)}")
        except Exception:
            pass

        return "\n".join(lines)
    except Exception:
        return ""


async def build_drama_context_block(
    drama_id: str,
    *,
    budget_chars: int = 4000,
    world_chars: int = 1200,
    characters_chars: int = 1600,
    outline_chars: int = 1600,
    episodes_chars: int = 2400,
    focus_episode_chars: int = 12000,
    sections: Optional[frozenset[str]] = None,
    focus_episode: Optional[int] = None,
    query: str = "",
    include_catalog: bool = True,
) -> str:
    """返回「当前作品上下文」：索引 + 按需摘要 + 焦点集全文。

    sections 指定注入部分（title/genre/description/world/characters/outline/episodes），
    None 表示全部。focus_episode / query 中的「第N集」会优先注入该集正文。
    """
    if not drama_id:
        return ""
    try:
        from utils.drama_manager import get_drama_manager

        mgr = get_drama_manager()
        drama = await mgr.get_drama(drama_id)
        if not drama:
            return ""

        if focus_episode is None:
            focus_episode = extract_focus_episode(query or "")

        want = set(sections) if sections is not None else None

        def _on(name: str) -> bool:
            return want is None or name in want

        parts: list[str] = []
        if _on("title"):
            parts.append(f"【当前作品】{drama.get('title') or '未命名'}")
        if _on("genre"):
            parts.append(f"【题材】{drama.get('genre') or ''}")
        desc = (drama.get("description") or "").strip()
        if desc and _on("description"):
            parts.append(f"【简介】{_clip(desc, 400)}")
        parts.append(
            f"【总集数】{drama.get('total_episodes') or ''}（已完成 {drama.get('completed_episodes') or 0} 集）"
        )

        if include_catalog:
            catalog = await build_drama_artifact_catalog(drama_id)
            if catalog:
                parts.append(catalog)

        bible = drama.get("bible") or {}
        world = (bible.get("world") or "").strip()
        characters = (bible.get("characters") or "").strip()
        outline = (drama.get("outline") or "").strip()

        # 有焦点集评估时，压缩大纲/设定摘要，把预算留给该集正文
        if focus_episode and _on("episodes"):
            world_chars = min(world_chars, 600)
            characters_chars = min(characters_chars, 900)
            outline_chars = min(outline_chars, 800)

        if world and _on("world"):
            parts.append(f"## 世界观/知识设定\n{_clip(world, world_chars)}")
        if characters and _on("characters"):
            parts.append(f"## 人物小传\n{_clip(characters, characters_chars)}")
        if outline and _on("outline"):
            parts.append(f"## 故事大纲\n{_clip(outline, outline_chars)}")

        if _on("episodes"):
            episodes = drama.get("episodes") or []
            done_eps = [e for e in episodes if e.get("status") == "done"]
            if done_eps:
                parts.append(f"【已写剧本】{len(done_eps)} 集")

            # 焦点集：全量（或大预算）注入 — 修复「评估第1集却只看见大纲」
            injected_focus = False
            if focus_episode:
                try:
                    ep = await mgr.get_episode(drama_id, int(focus_episode))
                    body = (ep.get("content") or "").strip()
                    if body:
                        parts.append(
                            f"## 第{focus_episode}集正文（评估/改写请以此为准）\n"
                            f"{_clip(body, focus_episode_chars)}"
                        )
                        injected_focus = True
                    else:
                        parts.append(
                            f"## 第{focus_episode}集\n（尚未写入正文，请先创作该集或换已写集评估）"
                        )
                        injected_focus = True
                except Exception:
                    pass

            # 非焦点场景：最近 2 集短摘要，避免 [-3:] 把早期集挤掉且又吃光预算
            if not injected_focus and done_eps:
                recent = done_eps[-2:]
                per_ep = max(200, episodes_chars // max(1, len(recent)))
                for e in recent:
                    try:
                        ep = await mgr.get_episode(drama_id, e.get("number") or 0)
                        body = (ep.get("content") or "").strip()
                        if body:
                            parts.append(
                                f"## 第{e.get('number')}集正文（摘要）\n{_clip(body, per_ep)}"
                            )
                    except Exception:
                        continue
                older = [e for e in done_eps if e not in recent]
                if older:
                    nums = ",".join(str(e.get("number")) for e in older)
                    parts.append(
                        f"（更早分集 {nums} 未展开，请用 read_drama_part(target=episode, episode_number=N) 读取）"
                    )

        block = "\n\n".join(parts)
        # 有焦点集时放宽总预算，避免大纲把正文砍掉
        effective_budget = budget_chars
        if focus_episode and _on("episodes"):
            effective_budget = max(budget_chars, focus_episode_chars + 3500)
        if len(block) > effective_budget:
            block = block[: max(0, effective_budget - 12)] + "…[截断]"
        return block
    except Exception:
        return ""


__all__ = [
    "build_drama_context_block",
    "build_drama_artifact_catalog",
    "context_sections_for",
    "extract_focus_episode",
]
