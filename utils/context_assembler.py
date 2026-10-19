"""
统一上下文组装 — 短剧写作用途
收敛 UnifiedMemory / Enhanced / Smart 多栈为一条明确模板。
接入五层 Agent Memory：规则 · 常驻 · 情节召回 · 语义事实 · 程序技能。
"""

from __future__ import annotations

from typing import Optional


def assemble_drama_context(
    *,
    title: str,
    episode_number: int,
    total_episodes: int,
    genre: str = "",
    description: str = "",
    bible: str = "",
    previous_summaries: str = "",
    skills: str = "",
    instruction: str = "",
    max_chars: int = 12000,
    memory_block: str = "",
) -> str:
    """按「Memory五层 + Skills + Bible + 前集摘要 + 本集任务」拼装。"""
    parts = [
        f"# 任务：撰写《{title}》第 {episode_number}/{total_episodes} 集",
        f"类型：{genre or '短剧'}",
        f"简介：{description or '无'}",
    ]
    if memory_block.strip():
        parts.append(memory_block.strip())
    if skills and not memory_block:
        # memory_block 已含 procedural 时避免重复灌 skills
        parts.append(skills)
    elif skills and memory_block and "## 程序技能" not in memory_block:
        parts.append(skills)
    if bible.strip() and (not memory_block or "## Bible" not in memory_block):
        parts.append("## Bible / 硬约束设定\n" + bible.strip()[:3500])
    if previous_summaries.strip():
        parts.append("## 前集上下文（保持连续性）\n" + previous_summaries.strip()[:4000])
    parts.append(
        f"## 本集任务\n请撰写第 {episode_number} 集完整剧本。"
        + (f"\n额外指令：{instruction}" if instruction else "")
        + "\n\n写作前请核对：未回收悬念(open_thread)、人物不变量、集末卡点。"
    )
    text = "\n\n".join(parts)
    if len(text) > max_chars:
        text = text[: max_chars - 20] + "\n…(已截断)"
    return text


def assemble_with_agent_memory(
    *,
    user_id: str,
    drama_id: str,
    title: str,
    episode_number: int,
    total_episodes: int,
    genre: str = "",
    description: str = "",
    bible: str = "",
    previous_summaries: str = "",
    instruction: str = "",
    query: str = "",
    max_chars: int = 12000,
) -> str:
    """生产路径：先召回五层记忆，再组装写作上下文。"""
    from utils.agent_memory import get_agent_memory_service

    svc = get_agent_memory_service()
    q = query or f"{title} 第{episode_number}集 {genre} {instruction}"
    bundle = svc.assemble_working_memory(
        user_id=user_id,
        drama_id=drama_id,
        query=q,
        bible=bible,
        budget_chars=min(8000, max_chars // 2),
    )
    return assemble_drama_context(
        title=title,
        episode_number=episode_number,
        total_episodes=total_episodes,
        genre=genre,
        description=description,
        bible="" if bundle.bible else bible,
        previous_summaries=previous_summaries,
        skills="",
        instruction=instruction,
        max_chars=max_chars,
        memory_block=bundle.to_prompt_block(),
    )


def compact_text(text: str, max_chars: int = 2000) -> str:
    """简单压缩：保留头尾。"""
    if not text or len(text) <= max_chars:
        return text or ""
    head = max_chars // 2
    tail = max_chars - head - 20
    return text[:head] + "\n…\n" + text[-tail:]
