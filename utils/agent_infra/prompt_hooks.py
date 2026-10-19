"""
Prompt / Session Hooks — 对照 OpenClaw prompt-and-session hooks

契约（cache 友好）：
- prependSystemContext / appendSystemContext  → 稳定、可缓存前缀
- prependDynamicSystemContext / appendDynamicSystemContext → 边界下方易变 system
- prependContext / appendContext → 本 turn 用户侧载体，不进永久 system
- systemPrompt → 覆盖整段基础 system（仅首个生效）
- toolsAllow → 收窄本 turn 工具面（多 hook 取交集）

阶段顺序（对齐 OpenClaw）：
  drain injections → agent_turn_prepare → before_prompt_build → assemble
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

HookHandler = Callable[..., Union[Dict[str, Any], Awaitable[Dict[str, Any]]]]


@dataclass
class HookRegistration:
    name: str
    event: str
    handler: HookHandler
    priority: int = 100  # 越大越先


@dataclass
class PromptHookResult:
    """合并后的 hook 贡献。"""

    system_prompt_override: Optional[str] = None
    prepend_system_context: List[str] = field(default_factory=list)
    append_system_context: List[str] = field(default_factory=list)
    prepend_dynamic_system_context: List[str] = field(default_factory=list)
    append_dynamic_system_context: List[str] = field(default_factory=list)
    prepend_context: List[str] = field(default_factory=list)
    append_context: List[str] = field(default_factory=list)
    tools_allow: Optional[List[str]] = None

    def merge_raw(self, raw: Optional[Dict[str, Any]]) -> None:
        if not raw:
            return
        if self.system_prompt_override is None and raw.get("systemPrompt"):
            self.system_prompt_override = str(raw["systemPrompt"])

        for key, attr in (
            ("prependSystemContext", "prepend_system_context"),
            ("appendSystemContext", "append_system_context"),
            ("prependDynamicSystemContext", "prepend_dynamic_system_context"),
            ("appendDynamicSystemContext", "append_dynamic_system_context"),
            ("prependContext", "prepend_context"),
            ("appendContext", "append_context"),
        ):
            val = raw.get(key)
            if val:
                getattr(self, attr).append(str(val))

        allow = raw.get("toolsAllow")
        if allow is not None:
            names = [str(x) for x in allow] if isinstance(allow, (list, tuple, set)) else []
            if self.tools_allow is None:
                self.tools_allow = names
            else:
                # 多 hook 取交集
                self.tools_allow = [n for n in self.tools_allow if n in set(names)]


@dataclass
class NextTurnInjection:
    """下一 turn 注入（对齐 OpenClaw enqueueNextTurnInjection）。"""

    plugin: str
    content: str
    idempotency_key: str = ""
    expires_at: float = 0.0
    as_dynamic_system: bool = True


class PromptHookRegistry:
    """进程内 hook 注册表。"""

    def __init__(self) -> None:
        self._hooks: List[HookRegistration] = []
        self._injections: Dict[str, List[NextTurnInjection]] = {}

    def on(
        self,
        event: str,
        handler: HookHandler,
        *,
        name: str = "",
        priority: int = 100,
    ) -> None:
        self._hooks.append(
            HookRegistration(
                name=name or getattr(handler, "__name__", "anon"),
                event=event,
                handler=handler,
                priority=priority,
            )
        )

    def clear(self, event: Optional[str] = None) -> None:
        if event is None:
            self._hooks.clear()
        else:
            self._hooks = [h for h in self._hooks if h.event != event]

    def enqueue_next_turn_injection(
        self,
        session_id: str,
        *,
        plugin: str,
        content: str,
        idempotency_key: str = "",
        expires_at: float = 0.0,
        as_dynamic_system: bool = True,
    ) -> None:
        bucket = self._injections.setdefault(session_id or "default", [])
        if idempotency_key:
            for existing in bucket:
                if existing.idempotency_key == idempotency_key and existing.plugin == plugin:
                    existing.content = content
                    existing.expires_at = expires_at
                    return
        bucket.append(
            NextTurnInjection(
                plugin=plugin,
                content=content,
                idempotency_key=idempotency_key,
                expires_at=expires_at,
                as_dynamic_system=as_dynamic_system,
            )
        )

    def drain_injections(self, session_id: str) -> List[NextTurnInjection]:
        import time

        now = time.time()
        sid = session_id or "default"
        pending = self._injections.pop(sid, [])
        kept: List[NextTurnInjection] = []
        drained: List[NextTurnInjection] = []
        for item in pending:
            if item.expires_at and item.expires_at < now:
                continue
            drained.append(item)
        # 消费即移除；失败重试由调用方重新 enqueue
        _ = kept
        return drained

    async def dispatch(self, event: str, ctx: Dict[str, Any]) -> PromptHookResult:
        result = PromptHookResult()
        handlers = sorted(
            [h for h in self._hooks if h.event == event],
            key=lambda h: (-h.priority, h.name),
        )
        # 只读快照：禁止 hook 就地改 history
        snapshot = {
            "prompt": ctx.get("prompt"),
            "messages": [dict(m) for m in (ctx.get("messages") or [])],
            "session_id": ctx.get("session_id"),
            "user_id": ctx.get("user_id"),
            "agent_id": ctx.get("agent_id"),
            "drama_id": ctx.get("drama_id"),
            "tools": list(ctx.get("tools") or []),
            "current_user_message": ctx.get("current_user_message"),
        }
        for reg in handlers:
            try:
                out = reg.handler(snapshot)
                if hasattr(out, "__await__"):
                    out = await out  # type: ignore[misc]
                if isinstance(out, dict):
                    result.merge_raw(out)
            except Exception as e:
                logger.warning("prompt hook %s/%s failed: %s", event, reg.name, e)
        return result


_GLOBAL_HOOKS: Optional[PromptHookRegistry] = None


def get_prompt_hooks() -> PromptHookRegistry:
    global _GLOBAL_HOOKS
    if _GLOBAL_HOOKS is None:
        _GLOBAL_HOOKS = PromptHookRegistry()
    return _GLOBAL_HOOKS


async def run_prompt_pipeline(
    *,
    system_prompt: str,
    messages: List[Dict[str, Any]],
    prompt: str = "",
    session_id: str = "default",
    user_id: str = "default_user",
    agent_id: str = "",
    drama_id: Optional[str] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    current_user_message: Optional[str] = None,
) -> PromptHookResult:
    """
    drain injections → agent_turn_prepare → before_prompt_build
    """
    registry = get_prompt_hooks()
    merged = PromptHookResult()

    for inj in registry.drain_injections(session_id):
        if inj.as_dynamic_system:
            merged.prepend_dynamic_system_context.append(inj.content)
        else:
            merged.prepend_context.append(inj.content)

    ctx = {
        "prompt": prompt,
        "messages": messages,
        "session_id": session_id,
        "user_id": user_id,
        "agent_id": agent_id,
        "drama_id": drama_id,
        "tools": tools or [],
        "current_user_message": current_user_message if current_user_message is not None else prompt,
        "system_prompt": system_prompt,
    }

    prepare = await registry.dispatch("agent_turn_prepare", ctx)
    merged.prepend_context.extend(prepare.prepend_context)
    merged.append_context.extend(prepare.append_context)

    build = await registry.dispatch("before_prompt_build", ctx)
    # systemPrompt 仅首个生效 —— prepare 不提供该字段，build 侧合并
    for part in (prepare, build):
        if merged.system_prompt_override is None and part.system_prompt_override:
            merged.system_prompt_override = part.system_prompt_override
        merged.prepend_system_context.extend(part.prepend_system_context)
        merged.append_system_context.extend(part.append_system_context)
        merged.prepend_dynamic_system_context.extend(part.prepend_dynamic_system_context)
        merged.append_dynamic_system_context.extend(part.append_dynamic_system_context)
        if part.tools_allow is not None:
            if merged.tools_allow is None:
                merged.tools_allow = list(part.tools_allow)
            else:
                allow_set = set(part.tools_allow)
                merged.tools_allow = [n for n in merged.tools_allow if n in allow_set]

    # prepare 的 prepend/appendContext 已加入；build 的也要加
    # （上面只 extend 了 system 侧，context 侧对 build 再补一次）
    merged.prepend_context.extend(build.prepend_context)
    merged.append_context.extend(build.append_context)

    return merged


def apply_turn_user_context(
    messages: List[Dict[str, Any]],
    *,
    prepend_context: List[str],
    append_context: List[str],
) -> List[Dict[str, Any]]:
    """
    将 per-turn user context 挂到当前 user 消息前后，不改写历史。
    对照 OpenClaw：prependContext/appendContext 是 turn carrier。
    """
    if not prepend_context and not append_context:
        return messages

    out = [dict(m) for m in messages]
    # 找到最后一条 user
    idx = None
    for i in range(len(out) - 1, -1, -1):
        if out[i].get("role") == "user":
            idx = i
            break
    if idx is None:
        # 无 user 消息时，作为独立 user 载体插入末尾
        blob_parts = []
        if prepend_context:
            blob_parts.append("\n\n".join(prepend_context))
        if append_context:
            blob_parts.append("\n\n".join(append_context))
        out.append({"role": "user", "content": "\n\n".join(blob_parts), "_transient": True})
        return out

    user_msg = dict(out[idx])
    content = str(user_msg.get("content") or "")
    prefix = "\n\n".join(p for p in prepend_context if p).strip()
    suffix = "\n\n".join(p for p in append_context if p).strip()
    pieces = [p for p in (prefix, content, suffix) if p]
    user_msg["content"] = "\n\n".join(pieces)
    # 投影标记：便于日后 replay 同一字节（OpenClaw stored projection）
    user_msg["_prompt_projection"] = user_msg["content"]
    out[idx] = user_msg
    return out
