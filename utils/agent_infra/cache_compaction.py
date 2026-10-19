"""
Cache-aware Compaction / Pruning — 对照 Pi self-compact + OpenClaw cache-ttl pruning

原则：
1. Compaction：摘要替换旧历史，保留 recent tail 原文；稳定 system 前缀不动
2. Self-compact：优先在「当前已缓存会话」末尾追加摘要指令（复用 prefix），
   失败再 fallback 到独立摘要请求
3. Pruning：默认 cache-ttl 模式——仅当 cache TTL 过期后才修剪旧 tool results，
   避免 idle 后整段 history 重新 cacheWrite
4. 已发送的 tool result 文本禁止再改写（首次截断即定稿）
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .prompt_cache import (
    PromptCacheConfig,
    clamp_tool_result_text,
    get_cache_session,
    normalize_prompt_text,
)

logger = logging.getLogger(__name__)

COMPACTION_SUMMARY_ROLE = "system"
COMPACTION_SUMMARY_PREFIX = "【Context Compaction Summary】\n"


@dataclass
class CompactionResult:
    messages: List[Dict[str, Any]]
    summary: str = ""
    dropped_count: int = 0
    kept_recent: int = 0
    mode: str = "none"  # none | prune | compact | self_compact
    details: Dict[str, Any] = field(default_factory=dict)


def estimate_chars(messages: List[Dict[str, Any]]) -> int:
    total = 0
    for m in messages:
        total += len(str(m.get("content") or ""))
        for tc in m.get("tool_calls") or []:
            fn = tc.get("function") or {}
            total += len(str(fn.get("arguments") or ""))
    return total


def split_system_and_rest(
    messages: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    systems = [m for m in messages if m.get("role") == "system"]
    rest = [m for m in messages if m.get("role") != "system"]
    return systems, rest


def should_compact(messages: List[Dict[str, Any]], config: PromptCacheConfig) -> bool:
    _, rest = split_system_and_rest(messages)
    return estimate_chars(rest) >= config.compact_threshold_chars


def prune_tool_results(
    messages: List[Dict[str, Any]],
    *,
    config: Optional[PromptCacheConfig] = None,
    session_id: str = "default",
    keep_recent_tool_results: int = 6,
) -> CompactionResult:
    """
    内存剪枝：缩短旧 tool 结果，不改写 transcript 中尚未发送过的语义边界。
    cache-ttl 模式：仅当 TTL 过期才执行。
    """
    cfg = config or PromptCacheConfig()
    state = get_cache_session(session_id)

    if cfg.pruning_mode == "off":
        return CompactionResult(messages=messages, mode="none")

    if cfg.pruning_mode == "cache-ttl" and not state.cache_ttl_expired(cfg.pruning_ttl_seconds):
        return CompactionResult(
            messages=messages,
            mode="none",
            details={"reason": "cache_ttl_valid", "ttl": cfg.pruning_ttl_seconds},
        )

    out = [dict(m) for m in messages]
    tool_indices = [i for i, m in enumerate(out) if m.get("role") == "tool"]
    if len(tool_indices) <= keep_recent_tool_results:
        return CompactionResult(messages=out, mode="none", details={"reason": "few_tool_results"})

    prune_upto = tool_indices[:-keep_recent_tool_results] if keep_recent_tool_results else tool_indices
    pruned = 0
    for i in prune_upto:
        content = str(out[i].get("content") or "")
        # 已截断标记的不再动，保证 replay 字节稳定
        if "...[tool result truncated]..." in content or "...[pruned]..." in content:
            continue
        if len(content) <= 200:
            continue
        # 定稿截断：同一会话后续 turn 复用此文本
        out[i] = dict(out[i])
        out[i]["content"] = clamp_tool_result_text(content, min(400, cfg.tool_result_max_chars // 4))
        if "...[tool result truncated]..." not in out[i]["content"]:
            out[i]["content"] = out[i]["content"][:180] + "\n...[pruned]..."
        out[i]["_pruned"] = True
        pruned += 1

    if pruned:
        # 剪枝后重置 TTL 窗口，后续请求可重新写入更短前缀
        state.touch_cache_write()

    return CompactionResult(
        messages=out,
        dropped_count=pruned,
        mode="prune" if pruned else "none",
        details={"pruned_tool_results": pruned},
    )


def _format_messages_for_summary(messages: List[Dict[str, Any]], max_chars: int = 12000) -> str:
    lines: List[str] = []
    for i, m in enumerate(messages):
        role = m.get("role", "?")
        content = str(m.get("content") or "")
        if m.get("tool_calls"):
            names = []
            for tc in m["tool_calls"]:
                fn = tc.get("function") or {}
                names.append(fn.get("name") or "?")
            content = content or f"(tool_calls: {', '.join(names)})"
        lines.append(f"[{i + 1}] {role.upper()}: {content[:800]}")
    text = "\n".join(lines)
    if len(text) > max_chars:
        text = text[: max_chars - 20] + "\n...[truncated]..."
    return text


def build_compaction_summary_prompt(older_messages: List[Dict[str, Any]]) -> str:
    """结构化摘要指令（对齐 OpenClaw compaction-safeguard 的信息保真要求）。"""
    history = _format_messages_for_summary(older_messages)
    return (
        "你正在为多轮 Agent 会话写压缩纪要。输出必须完整可独立阅读，供后续模型继续任务。\n"
        "请保留：当前目标、用户纠正、硬约束、已完成/待办、关键执行证据、下一步动作。\n"
        "不要输出工具调用；不要编造未出现的事实。\n\n"
        f"## 待压缩历史\n{history}\n\n"
        "## 输出格式\n"
        "**活跃目标：**\n...\n"
        "**约束与纠正：**\n- ...\n"
        "**已完成：**\n- ...\n"
        "**待办：**\n- ...\n"
        "**关键证据：**\n- ...\n"
        "**下一步：**\n..."
    )


async def self_compact_summary(
    *,
    client: Any,
    cached_messages: List[Dict[str, Any]],
    older_messages: List[Dict[str, Any]],
    max_tokens: int = 2048,
) -> Optional[str]:
    """
    Pi self-compact / cachepoint：在当前会话消息末尾追加摘要指令，
    复用已缓存 prefix，而不是把历史重放成全新独立 prompt。
    """
    if client is None or not older_messages:
        return None
    try:
        msgs = [dict(m) for m in cached_messages]
        # 仅把「待压缩」部分的索引提示放在末尾 user，避免改动 prefix
        instruction = (
            "请基于当前对话上下文，为较早的历史写一段压缩纪要"
            "（活跃目标 / 约束 / 已完成 / 待办 / 关键证据 / 下一步）。"
            "不要调用工具。只输出纪要正文。"
        )
        msgs.append({"role": "user", "content": instruction})
        if hasattr(client, "chat"):
            text = await client.chat(msgs, max_tokens=max_tokens, temperature=0.2)
        elif hasattr(client, "chat_with_response"):
            resp = await client.chat_with_response(msgs, max_tokens=max_tokens, temperature=0.2)
            text = getattr(resp, "content", None) or ""
        else:
            return None
        text = (text or "").strip()
        if not text or "<tool_call>" in text:
            return None
        return text
    except Exception as e:
        logger.info("self_compact failed, will fallback: %s", e)
        return None


async def fallback_summarize(
    *,
    client: Any,
    older_messages: List[Dict[str, Any]],
    max_tokens: int = 2048,
) -> str:
    """独立摘要请求（Pi/OpenClaw fallback）。"""
    prompt = build_compaction_summary_prompt(older_messages)
    if client is None:
        return _heuristic_summary(older_messages)
    try:
        msgs = [
            {"role": "system", "content": "你是上下文压缩器。只输出结构化纪要。"},
            {"role": "user", "content": prompt},
        ]
        if hasattr(client, "chat"):
            text = await client.chat(msgs, max_tokens=max_tokens, temperature=0.2)
        else:
            text = None
        text = (text or "").strip()
        return text or _heuristic_summary(older_messages)
    except Exception as e:
        logger.warning("fallback summarize failed: %s", e)
        return _heuristic_summary(older_messages)


def _heuristic_summary(messages: List[Dict[str, Any]]) -> str:
    users = [str(m.get("content") or "")[:200] for m in messages if m.get("role") == "user"]
    tools = [m for m in messages if m.get("role") == "tool"]
    return (
        f"压缩纪要（启发式）：共 {len(messages)} 条消息，"
        f"用户回合 {len(users)}，工具结果 {len(tools)}。"
        f"最近用户意图摘要：{' | '.join(users[-3:]) or '无'}"
    )


async def compact_messages(
    messages: List[Dict[str, Any]],
    *,
    client: Any = None,
    config: Optional[PromptCacheConfig] = None,
    session_id: str = "default",
    force: bool = False,
    prefer_self_compact: bool = True,
) -> CompactionResult:
    """
    Cache-preserving compaction：
    [stable system...] + [summary message] + [recent tail]
    不改写 stable system；summary 落在动态区（作为独立 system 或 user 旁注）。
    """
    cfg = config or PromptCacheConfig()
    if not force and not should_compact(messages, cfg):
        # 仍可做 TTL 剪枝
        return prune_tool_results(messages, config=cfg, session_id=session_id)

    systems, rest = split_system_and_rest(messages)
    keep_n = max(2, cfg.keep_recent_messages)
    if len(rest) <= keep_n:
        return prune_tool_results(messages, config=cfg, session_id=session_id)

    older = rest[:-keep_n]
    recent = rest[-keep_n:]

    summary: Optional[str] = None
    mode = "compact"
    if prefer_self_compact and client is not None:
        # 用「当前 systems + older」作为缓存前缀延伸（近似 Pi）
        prefix_msgs = systems + older
        summary = await self_compact_summary(
            client=client,
            cached_messages=prefix_msgs,
            older_messages=older,
        )
        if summary:
            mode = "self_compact"

    if not summary:
        summary = await fallback_summarize(client=client, older_messages=older)
        mode = "compact"

    summary = normalize_prompt_text(summary)
    summary_msg: Dict[str, Any] = {
        "role": COMPACTION_SUMMARY_ROLE,
        "content": COMPACTION_SUMMARY_PREFIX + summary,
        "_cacheable": False,  # 摘要变更不应打爆稳定前缀
        "_compaction": True,
        "_compacted_at": datetime.now().isoformat(),
    }

    # systems 保持原序；去掉旧的 compaction 摘要避免堆积
    stable_systems = [
        m for m in systems
        if not (m.get("_compaction") or str(m.get("content") or "").startswith(COMPACTION_SUMMARY_PREFIX))
    ]
    new_messages = stable_systems + [summary_msg] + recent

    state = get_cache_session(session_id)
    state.compaction_count += 1
    state.touch_cache_write()

    # 压缩后再做一次轻量剪枝（此时 TTL 已重置，cache-ttl 可能跳过——强制 always 一次）
    pruned = prune_tool_results(
        new_messages,
        config=PromptCacheConfig(
            **{
                **cfg.__dict__,
                "pruning_mode": "always",
            }
        ),
        session_id=session_id,
    )

    return CompactionResult(
        messages=pruned.messages,
        summary=summary,
        dropped_count=len(older),
        kept_recent=len(recent),
        mode=mode,
        details={
            "older_count": len(older),
            "recent_count": len(recent),
            "compaction_count": state.compaction_count,
            "pruned_tool_results": pruned.dropped_count,
        },
    )
