"""
Context Budget — token/字符预算 + Prompt-Cache 友好组装

对照 OpenClaw / Pi：
- rules / 静态指引 → stable prefix（可缓存）
- memory / runtime / 召回 → dynamic suffix（边界下方）
- history 只裁尾、不改写已发送内容
- hooks 的 static/dynamic/user context 分层落地
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .prompt_cache import (
    AssembledPrompt,
    PromptCacheConfig,
    assemble_system_parts,
    build_openai_cache_extra,
    fingerprint_prefix,
    get_cache_session,
    load_prompt_cache_config,
    sort_tools_for_cache,
    strip_internal_fields,
)
from .prompt_hooks import apply_turn_user_context, run_prompt_pipeline


@dataclass
class ContextBudget:
    total_chars: int = 24000
    rules_chars: int = 3000
    memory_chars: int = 6000
    drama_chars: int = 4000
    history_chars: int = 10000
    tools_chars: int = 3000
    scratch_chars: int = 2000

    def clamp(self) -> "ContextBudget":
        parts = [
            self.rules_chars,
            self.memory_chars,
            self.drama_chars,
            self.history_chars,
            self.tools_chars,
            self.scratch_chars,
        ]
        s = sum(parts)
        if s <= self.total_chars:
            return self
        scale = self.total_chars / max(s, 1)
        return ContextBudget(
            total_chars=self.total_chars,
            rules_chars=int(self.rules_chars * scale),
            memory_chars=int(self.memory_chars * scale),
            drama_chars=int(self.drama_chars * scale),
            history_chars=int(self.history_chars * scale),
            tools_chars=int(self.tools_chars * scale),
            scratch_chars=int(self.scratch_chars * scale),
        )


def truncate_text(text: str, max_chars: int) -> str:
    if not text or len(text) <= max_chars:
        return text or ""
    keep = max(0, max_chars - 20)
    return text[:keep] + "\n...[truncated]..."


def trim_history(messages: List[Dict[str, Any]], max_chars: int) -> List[Dict[str, Any]]:
    """从旧到新裁剪，保留最近消息。不改写已保留消息的 content（cache 连贯）。"""
    if not messages:
        return messages
    systems = [m for m in messages if m.get("role") == "system"]
    rest = [m for m in messages if m.get("role") != "system"]
    budget = max_chars
    kept_rev: List[Dict[str, Any]] = []
    for m in reversed(rest):
        size = len(str(m.get("content") or ""))
        if size > budget and kept_rev:
            break
        if size > budget:
            # 仅对「即将纳入但超预算」的单条做首次截断；一旦留下就不再改
            if m.get("_content_finalized"):
                break
            m = dict(m)
            m["content"] = truncate_text(str(m.get("content") or ""), budget)
            m["_content_finalized"] = True
            kept_rev.append(m)
            break
        kept_rev.append(m)
        budget -= size
    kept = list(reversed(kept_rev))
    return systems + kept


async def _load_memory_block(
    *,
    drama_id: Optional[str],
    user_id: str,
    query: str,
    budget_chars: int,
) -> str:
    if not drama_id:
        return ""
    try:
        from utils.agent_memory import get_agent_memory_service

        svc = get_agent_memory_service()
        bundle = svc.assemble_working_memory(
            drama_id=drama_id,
            user_id=user_id,
            query=query or "",
            budget_chars=budget_chars,
        )
        block = bundle.to_prompt_block() if hasattr(bundle, "to_prompt_block") else str(bundle)
        return truncate_text(block or "", budget_chars)
    except Exception:
        return ""


async def _load_drama_context_block(
    drama_id: Optional[str],
    budget_chars: int,
    agent_id: str = "",
    query: str = "",
) -> str:
    """共享作品上下文：索引 + 摘要 + 焦点集全文（单一事实源，按 agent 类别裁剪）。"""
    if not drama_id:
        return ""
    try:
        from utils.drama_context import (
            build_drama_context_block,
            context_sections_for,
            extract_focus_episode,
        )

        sections = None
        if agent_id:
            try:
                from config.agents import get_agent_config

                cfg = get_agent_config(agent_id)
                if cfg:
                    sections = context_sections_for(cfg.get("category"))
            except Exception:
                sections = None

        focus_ep = extract_focus_episode(query or "")
        effective = budget_chars
        focus_chars = min(12000, max(budget_chars, 4000))
        if focus_ep and (sections is None or "episodes" in (sections or set())):
            effective = max(budget_chars, focus_chars + 3500)

        block = await build_drama_context_block(
            drama_id,
            budget_chars=effective,
            focus_episode_chars=focus_chars,
            sections=sections,
            focus_episode=focus_ep,
            query=query or "",
            include_catalog=True,
        )
        return truncate_text(block or "", effective)
    except Exception:
        return ""


async def assemble_budgeted_messages(
    *,
    system_prompt: str,
    user_messages: List[Dict[str, Any]],
    drama_id: Optional[str] = None,
    user_id: str = "default_user",
    budget: Optional[ContextBudget] = None,
    query: str = "",
    session_id: str = "default",
    agent_id: str = "",
    tools: Optional[List[Dict[str, Any]]] = None,
    cache_config: Optional[PromptCacheConfig] = None,
    run_hooks: bool = True,
    split_system_messages: bool = True,
    stable_extra: Optional[List[str]] = None,
    dynamic_extra: Optional[List[str]] = None,
    model: str = "",
    for_provider: bool = True,
) -> List[Dict[str, Any]]:
    """
    组装带预算且 prompt-cache 友好的消息。

    布局：
      [system stable]  ← rules / static hooks
      [system dynamic] ← memory / runtime / dynamic hooks
      [history…]
      [user + turn context]
    """
    assembled = await assemble_prompt_bundle(
        system_prompt=system_prompt,
        user_messages=user_messages,
        drama_id=drama_id,
        user_id=user_id,
        budget=budget,
        query=query,
        session_id=session_id,
        agent_id=agent_id,
        tools=tools,
        cache_config=cache_config,
        run_hooks=run_hooks,
        split_system_messages=split_system_messages,
        stable_extra=stable_extra,
        dynamic_extra=dynamic_extra,
        model=model,
    )
    if for_provider:
        return strip_internal_fields(assembled.messages)
    return assembled.messages


async def assemble_budgeted_prompt(
    *,
    system_prompt: str,
    user_messages: List[Dict[str, Any]],
    drama_id: Optional[str] = None,
    user_id: str = "default_user",
    budget: Optional[ContextBudget] = None,
    query: str = "",
    session_id: str = "default",
    agent_id: str = "",
    tools: Optional[List[Dict[str, Any]]] = None,
    cache_config: Optional[PromptCacheConfig] = None,
    run_hooks: bool = True,
    split_system_messages: bool = True,
    stable_extra: Optional[List[str]] = None,
    dynamic_extra: Optional[List[str]] = None,
    model: str = "",
) -> AssembledPrompt:
    """薄封装 assemble_prompt_bundle，返回完整 AssembledPrompt（含 extra_body / prompt_cache_key）。

    供 caller 把 cache 元数据（prompt_cache_key 等）一并透传给 run_tool_loop，
    而不改变 assemble_budgeted_messages 既有的「只返回 messages」契约。
    """
    return await assemble_prompt_bundle(
        system_prompt=system_prompt,
        user_messages=user_messages,
        drama_id=drama_id,
        user_id=user_id,
        budget=budget,
        query=query,
        session_id=session_id,
        agent_id=agent_id,
        tools=tools,
        cache_config=cache_config,
        run_hooks=run_hooks,
        split_system_messages=split_system_messages,
        stable_extra=stable_extra,
        dynamic_extra=dynamic_extra,
        model=model,
    )


async def assemble_prompt_bundle(
    *,
    system_prompt: str,
    user_messages: List[Dict[str, Any]],
    drama_id: Optional[str] = None,
    user_id: str = "default_user",
    budget: Optional[ContextBudget] = None,
    query: str = "",
    session_id: str = "default",
    agent_id: str = "",
    tools: Optional[List[Dict[str, Any]]] = None,
    cache_config: Optional[PromptCacheConfig] = None,
    run_hooks: bool = True,
    split_system_messages: bool = True,
    stable_extra: Optional[List[str]] = None,
    dynamic_extra: Optional[List[str]] = None,
    model: str = "",
    compact_if_needed: bool = False,
    llm_client: Any = None,
) -> AssembledPrompt:
    """完整组装，返回 messages + cache 元数据。"""
    budget = (budget or ContextBudget()).clamp()
    cfg = cache_config or load_prompt_cache_config()
    tools = sort_tools_for_cache(tools)

    hook_result = None
    if run_hooks:
        hook_result = await run_prompt_pipeline(
            system_prompt=system_prompt,
            messages=user_messages,
            prompt=query or "",
            session_id=session_id,
            user_id=user_id,
            agent_id=agent_id,
            drama_id=drama_id,
            tools=tools,
            current_user_message=query,
        )
        if hook_result.system_prompt_override:
            system_prompt = hook_result.system_prompt_override
        if hook_result.tools_allow is not None and tools:
            allow = set(hook_result.tools_allow)
            tools = [
                t
                for t in tools
                if (t.get("function") or {}).get("name") in allow or t.get("name") in allow
            ]

    memory_block = await _load_memory_block(
        drama_id=drama_id,
        user_id=user_id,
        query=query,
        budget_chars=budget.memory_chars,
    )
    drama_context_block = await _load_drama_context_block(
        drama_id, budget.drama_chars, agent_id=agent_id, query=query or ""
    )

    dyn_blocks: List[str] = list(dynamic_extra or [])
    # 共享作品上下文放在记忆之前（更基础、更权威）
    if drama_context_block:
        dyn_blocks.append(drama_context_block)
    if memory_block:
        dyn_blocks.append(memory_block)

    # L1 Wiki Index：常驻稳定前缀（若 system 尚未包含）
    stable_blocks: List[str] = list(stable_extra or [])
    if "Knowledge Wiki Index" not in (system_prompt or "") and not any(
        "Knowledge Wiki Index" in (s or "") for s in stable_blocks
    ):
        try:
            from utils.llm_wiki import build_wiki_index_prompt, ensure_wiki_bootstrapped

            ensure_wiki_bootstrapped()
            wiki_idx = build_wiki_index_prompt(max_chars=min(6000, max(budget.rules_chars, 4000)))
            if wiki_idx:
                stable_blocks.append(wiki_idx)
        except Exception:
            pass

    prepend_sys = "\n\n".join(hook_result.prepend_system_context) if hook_result else ""
    append_sys = "\n\n".join(hook_result.append_system_context) if hook_result else ""
    prepend_dyn = "\n\n".join(hook_result.prepend_dynamic_system_context) if hook_result else ""
    append_dyn = "\n\n".join(hook_result.append_dynamic_system_context) if hook_result else ""

    parts = assemble_system_parts(
        system_prompt=truncate_text(system_prompt, budget.rules_chars),
        stable_extra=stable_blocks,
        dynamic_extra=dyn_blocks,
        prepend_system=prepend_sys,
        append_system=append_sys,
        prepend_dynamic_system=prepend_dyn,
        append_dynamic_system=append_dyn,
    )

    messages: List[Dict[str, Any]] = parts.to_system_messages(split_messages=split_system_messages)

    history = trim_history(user_messages, budget.history_chars)
    for m in history:
        if m.get("role") == "system":
            # 历史里的 system（如旧 compaction）保留，但标为不可缓存前缀
            item = dict(m)
            item.setdefault("_cacheable", False)
            messages.append(item)
            continue
        messages.append(dict(m))

    if hook_result:
        messages = apply_turn_user_context(
            messages,
            prepend_context=hook_result.prepend_context,
            append_context=hook_result.append_context,
        )

    compaction_applied = False
    if compact_if_needed:
        from .cache_compaction import compact_messages, should_compact

        if should_compact(messages, cfg):
            result = await compact_messages(
                messages,
                client=llm_client,
                config=cfg,
                session_id=session_id,
            )
            messages = result.messages
            compaction_applied = result.mode != "none"

    state = get_cache_session(session_id)
    fp = fingerprint_prefix(parts.stable_prefix, tools)
    state.last_prompt_fingerprint = fp
    extra = build_openai_cache_extra(
        session_id=session_id,
        agent_id=agent_id,
        model=model,
        cache_retention=cfg.cache_retention,
        supports_prompt_cache_key=cfg.supports_prompt_cache_key,
        config=cfg,
    )

    return AssembledPrompt(
        messages=messages,
        parts=parts,
        prompt_cache_key=extra.get("prompt_cache_key", ""),
        prefix_fingerprint=fp,
        extra_body=extra,
        compaction_applied=compaction_applied,
    )
