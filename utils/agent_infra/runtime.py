"""
Agent Runtime — 最小可用 LLM-native tool-calling loop

while not done:
  LLM(messages, tools) → content | tool_calls
  execute tools via ToolHarness
  append tool results
  checkpoint (optional)
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)  # ingress/egress/substrate soft-fail logs

OnStepCallback = Callable[[Dict[str, Any]], Awaitable[None]]


@dataclass
class AgentLoopResult:
    content: str
    messages: List[Dict[str, Any]]
    tool_history: List[Dict[str, Any]] = field(default_factory=list)
    steps: int = 0
    finish_reason: str = "stop"
    trace_id: str = ""
    aborted: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "steps": self.steps,
            "finish_reason": self.finish_reason,
            "trace_id": self.trace_id,
            "aborted": self.aborted,
            "tool_history": self.tool_history,
            "messages": self.messages,
        }


def _parse_fallback_tool_calls(content: str) -> List[Dict[str, Any]]:
    """当 provider 不返回原生 tool_calls 时，解析 XML / JSON 伪调用。"""
    calls: List[Dict[str, Any]] = []
    if not content:
        return calls

    for m in re.finditer(
        r"<tool_call>\s*<name>(.*?)</name>\s*<arguments>(.*?)</arguments>\s*</tool_call>",
        content,
        re.DOTALL | re.IGNORECASE,
    ):
        name = m.group(1).strip()
        raw_args = m.group(2).strip()
        try:
            args = json.loads(raw_args) if raw_args else {}
        except json.JSONDecodeError:
            args = {"input": raw_args}
        calls.append(
            {
                "id": f"call_{uuid.uuid4().hex[:10]}",
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(args, ensure_ascii=False)},
            }
        )
    if calls:
        return calls

    # ```tool_call\n{"name":"...","arguments":{...}}\n```
    for m in re.finditer(r"```tool_call\s*(\{.*?\})\s*```", content, re.DOTALL):
        try:
            obj = json.loads(m.group(1))
            name = obj.get("name") or obj.get("tool")
            args = obj.get("arguments") or obj.get("params") or {}
            if name:
                calls.append(
                    {
                        "id": f"call_{uuid.uuid4().hex[:10]}",
                        "type": "function",
                        "function": {
                            "name": name,
                            "arguments": json.dumps(args, ensure_ascii=False)
                            if not isinstance(args, str)
                            else args,
                        },
                    }
                )
        except json.JSONDecodeError:
            continue
    return calls


def _extract_usage(resp_usage: Any) -> Dict[str, Any]:
    """归一化 usage，含 prompt-cache 计数。"""
    if not resp_usage:
        return {}
    if isinstance(resp_usage, dict):
        raw = dict(resp_usage)
    else:
        raw = {
            "prompt_tokens": getattr(resp_usage, "prompt_tokens", 0) or 0,
            "completion_tokens": getattr(resp_usage, "completion_tokens", 0) or 0,
            "total_tokens": getattr(resp_usage, "total_tokens", 0) or 0,
        }
        ptd = getattr(resp_usage, "prompt_tokens_details", None)
        if ptd is not None:
            raw["prompt_tokens_details"] = {
                "cached_tokens": getattr(ptd, "cached_tokens", 0) or 0,
                "cache_write_tokens": getattr(ptd, "cache_write_tokens", 0) or 0,
            }
        for attr in ("cache_read_input_tokens", "cache_creation_input_tokens", "cached_tokens"):
            if getattr(resp_usage, attr, None) is not None:
                raw[attr] = getattr(resp_usage, attr)
    try:
        from utils.agent_infra.prompt_cache import normalize_cache_usage

        norm = normalize_cache_usage(raw)
        raw.update(norm)
    except Exception:
        pass
    return raw


async def _llm_with_tools(
    client: Any,
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]],
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    统一拿到 {content, tool_calls, finish_reason, usage}。
    优先走 client.chat_with_tools；其次 OpenAI-compatible raw client；最后纯文本 + fallback 解析。
    """
    try:
        from utils.agent_infra.prompt_cache import sort_tools_for_cache, strip_internal_fields

        tools = sort_tools_for_cache(tools) if tools else tools
        messages = strip_internal_fields(messages)
    except Exception:
        pass

    # prompt_cache_key / retention 通过 extra_body 或顶层透传
    cache_extra = kwargs.pop("prompt_cache_extra", None) or kwargs.pop("extra_body", None) or {}

    if hasattr(client, "chat_with_tools"):
        result = await client.chat_with_tools(
            messages, tools=tools, extra_body=cache_extra or None, **kwargs
        )
        usage = _extract_usage(result.get("usage"))
        result = dict(result)
        result["usage"] = usage
        return result

    openai_client = getattr(client, "client", None)
    if openai_client is not None and tools:
        model = kwargs.get("model") or getattr(client, "model", None)
        create_kwargs: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", getattr(client, "temperature", 0.7)),
            "tools": tools,
            "tool_choice": kwargs.get("tool_choice", "auto"),
        }
        max_tokens = kwargs.get("max_tokens", getattr(client, "max_tokens", None))
        if max_tokens:
            create_kwargs["max_tokens"] = max_tokens
        if cache_extra:
            # OpenAI SDK：未知字段进 extra_body
            create_kwargs["extra_body"] = dict(cache_extra)
        resp = await openai_client.chat.completions.create(**create_kwargs)
        msg = resp.choices[0].message
        tool_calls = []
        if getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                tool_calls.append(
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments or "{}",
                        },
                    }
                )
        usage = _extract_usage(getattr(resp, "usage", None))
        return {
            "content": msg.content or "",
            "tool_calls": tool_calls,
            "finish_reason": resp.choices[0].finish_reason or "stop",
            "usage": usage,
        }

    # 无原生 tools：在 system 里提示 XML，再 fallback 解析
    content = await client.chat(messages, **kwargs)
    tool_calls = _parse_fallback_tool_calls(content or "")
    return {
        "content": content or "",
        "tool_calls": tool_calls,
        "finish_reason": "tool_calls" if tool_calls else "stop",
        "usage": {},
    }


async def run_tool_loop(
    *,
    client: Any,
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]] = None,
    harness: Any = None,
    tool_ctx: Any = None,
    max_steps: int = 8,
    checkpoint_store: Any = None,
    checkpoint_id: Optional[str] = None,
    on_step: Optional[OnStepCallback] = None,
    abort_check: Optional[Callable[[], bool]] = None,
    trace_id: Optional[str] = None,
    skip_ingress: bool = False,
    workload_id: Optional[str] = None,
    suspend_on_complete: bool = False,
    **llm_kwargs: Any,
) -> AgentLoopResult:
    """
    Agent Loop（Harness 核心）。

    Ingress 过滤入站消息；Egress 在 ToolHarness.execute 拦截工具/网络；
    Substrate 负责 checkpoint / suspend（本函数决定何时调用）。

    messages: OpenAI 风格对话
    tools: OpenAI tools schema（可从 ToolRegistry.openai_tools() 取）
    harness: ToolHarness；有 tool_calls 时必须提供
    """
    from utils.agent_infra.observability import get_agent_metrics

    metrics = get_agent_metrics()
    tid = trace_id or f"trace_{uuid.uuid4().hex[:12]}"

    # --- Ingress：进 Harness 前 ---
    msgs = [dict(m) for m in messages]
    if not skip_ingress:
        try:
            from utils.agent_infra.gateway import get_ingress_gateway, get_egress_gateway

            ingress = get_ingress_gateway()
            prepared = ingress.prepare(
                messages=msgs,
                user=getattr(tool_ctx, "user", None) if tool_ctx else None,
                user_id=getattr(tool_ctx, "user_id", None) if tool_ctx else None,
                agent_id=getattr(tool_ctx, "agent_id", None) if tool_ctx else None,
                session_id=getattr(tool_ctx, "session_id", None) if tool_ctx else None,
            )
            if not prepared.allowed:
                return AgentLoopResult(
                    content=f"[ingress denied] {prepared.reason}",
                    messages=msgs,
                    tool_history=[],
                    steps=0,
                    finish_reason="ingress_denied",
                    trace_id=tid,
                    aborted=True,
                )
            msgs = list(prepared.filtered_payload or msgs)

            # Egress：过滤暴露给模型的工具 schema + 模型白名单
            model_name = llm_kwargs.get("model") or getattr(client, "model", None)
            model_dec = get_egress_gateway().check_model(model_name if isinstance(model_name, str) else None)
            if not model_dec.allowed:
                return AgentLoopResult(
                    content=f"[egress denied] {model_dec.reason}",
                    messages=msgs,
                    tool_history=[],
                    steps=0,
                    finish_reason="egress_denied",
                    trace_id=tid,
                    aborted=True,
                )
            if tools:
                tools = get_egress_gateway().filter_tools_schema(
                    tools, user=getattr(tool_ctx, "user", None) if tool_ctx else None
                )
        except Exception as e:
            logger.exception("ingress/egress prepare failed (fail-closed)")
            return AgentLoopResult(
                content=f"[gateway denied] 策略检查失败: {e}",
                messages=msgs,
                tool_history=[],
                steps=0,
                finish_reason="ingress_denied",
                trace_id=tid,
                aborted=True,
            )

    # Substrate：若有 workload，绑定 checkpoint
    substrate = None
    wl_id = workload_id or (getattr(tool_ctx, "workload_id", None) if tool_ctx else None)
    if wl_id:
        try:
            from utils.agent_infra.substrate import get_agent_substrate

            substrate = get_agent_substrate()
            snap = await substrate.load(wl_id)
            if snap and snap.status == "suspended":
                snap = await substrate.resume(wl_id)
            if snap and snap.messages and len(msgs) <= 1:
                # 恢复时优先用快照对话（调用方未带全量 history）
                msgs = list(snap.messages)
            if snap and not checkpoint_id:
                checkpoint_id = snap.checkpoint_id
                if checkpoint_store is None:
                    from utils.agent_infra.checkpoint import CheckpointStore

                    checkpoint_store = CheckpointStore()
        except Exception as e:
            logger.warning("substrate bind soft-fail: %s", e)

    history: List[Dict[str, Any]] = []
    final_content = ""
    finish_reason = "stop"

    # Prompt-cache：工具按 name 排序，保证 tools 前缀稳定
    def _clamp_tool_text(text: str, max_chars: int) -> str:
        if not text or max_chars <= 0 or len(text) <= max_chars:
            return text or ""
        return text[: max(0, max_chars - 24)] + "\n...[tool result truncated]..."

    try:
        from utils.agent_infra.prompt_cache import (
            PromptCacheConfig,
            clamp_tool_result_text as _clamp_tool_text,
            get_cache_session,
            sort_tools_for_cache,
        )

        tools = sort_tools_for_cache(tools) if tools else tools
        cache_cfg = llm_kwargs.pop("cache_config", None) or PromptCacheConfig()
        session_id = (
            llm_kwargs.pop("session_id", None)
            or getattr(tool_ctx, "session_id", None)
            or checkpoint_id
            or "default"
        )
        cache_state = get_cache_session(str(session_id))
        tool_result_max = int(getattr(cache_cfg, "tool_result_max_chars", 8000) or 8000)
    except Exception:
        cache_cfg = None
        cache_state = None
        tool_result_max = 8000

    # 若无原生 tools API，注入 fallback 协议提示（进入 dynamic 侧，避免打爆稳定前缀）
    if tools and not hasattr(getattr(client, "client", None), "chat"):
        pass  # openai path handles tools
    elif tools and getattr(client, "client", None) is None:
        hint = (
            "当你需要调用工具时，使用如下 XML：\n"
            "<tool_call><name>TOOL_NAME</name><arguments>{\"k\":...}</arguments></tool_call>\n"
            f"可用工具: {', '.join(t['function']['name'] for t in tools if 'function' in t)}"
        )
        msgs.insert(0, {"role": "system", "content": hint, "_cacheable": False})

    for step in range(max_steps):
        if abort_check and abort_check():
            return AgentLoopResult(
                content=final_content,
                messages=msgs,
                tool_history=history,
                steps=step,
                finish_reason="aborted",
                trace_id=tid,
                aborted=True,
            )
        if tool_ctx is not None and getattr(tool_ctx, "aborted", False):
            return AgentLoopResult(
                content=final_content,
                messages=msgs,
                tool_history=history,
                steps=step,
                finish_reason="aborted",
                trace_id=tid,
                aborted=True,
            )

        # 协议内预判式压缩：只动动态区（稳定 system 前缀不动），摘要替换旧历史 + 保留 recent tail
        if cache_cfg and getattr(cache_cfg, "auto_compact", False):
            from utils.agent_infra.cache_compaction import compact_messages, should_compact

            if should_compact(msgs, cache_cfg):
                compacted = await compact_messages(
                    msgs, client=client, config=cache_cfg, session_id=session_id
                )
                msgs = list(compacted.messages)
                logger.info(
                    "agent loop auto-compact mode=%s dropped=%d kept_recent=%d",
                    compacted.mode,
                    compacted.dropped_count,
                    compacted.kept_recent,
                )

        from utils.agent_infra.otel import otel_span

        with metrics.timer("agent_loop_llm"), otel_span(
            "agent_loop.llm", {"step": str(step), "trace_id": tid}
        ):
            result = await _llm_with_tools(client, msgs, tools, **llm_kwargs)

        content = result.get("content") or ""
        tool_calls = result.get("tool_calls") or []
        finish_reason = result.get("finish_reason") or ("tool_calls" if tool_calls else "stop")
        usage = result.get("usage") or {}
        if usage:
            metrics.record_tokens(
                prompt=usage.get("prompt_tokens", 0),
                completion=usage.get("completion_tokens", 0),
            )
            if cache_state is not None:
                # 任意成功请求刷新 cache TTL 窗口（对齐 OpenClaw appendCacheTtlTimestamp）
                cache_state.touch_cache_write()
                if usage.get("cacheRead") or usage.get("cacheWrite"):
                    metrics.inc(
                        "prompt_cache_hits",
                        labels={"read": str(bool(usage.get("cacheRead")))},
                    )

        if on_step:
            await on_step(
                {
                    "type": "llm",
                    "step": step,
                    "content": content,
                    "tool_calls": tool_calls,
                    "trace_id": tid,
                }
            )

        if not tool_calls:
            final_content = content
            msgs.append({"role": "assistant", "content": content})
            if checkpoint_store and checkpoint_id:
                await checkpoint_store.save(
                    checkpoint_id,
                    {
                        "messages": msgs,
                        "step": step,
                        "tool_history": history,
                        "trace_id": tid,
                        "status": "completed",
                    },
                )
            if substrate and wl_id:
                try:
                    await substrate.checkpoint(
                        wl_id,
                        messages=msgs,
                        step=step,
                        tool_history=history,
                        status="completed",
                        trace_id=tid,
                    )
                    if suspend_on_complete:
                        await substrate.suspend(wl_id, reason="completed")
                except Exception as e:
                    logger.debug("substrate checkpoint: %s", e)
            return AgentLoopResult(
                content=final_content,
                messages=msgs,
                tool_history=history,
                steps=step + 1,
                finish_reason=finish_reason,
                trace_id=tid,
            )

        # assistant message with tool_calls
        assistant_msg: Dict[str, Any] = {"role": "assistant", "content": content or None}
        assistant_msg["tool_calls"] = tool_calls
        msgs.append(assistant_msg)

        if harness is None:
            raise RuntimeError("tool_calls 需要传入 ToolHarness (harness=...)")

        for tc in tool_calls:
            fn = tc.get("function") or {}
            name = fn.get("name") or ""
            raw_args = fn.get("arguments") or "{}"
            try:
                params = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
            except json.JSONDecodeError:
                params = {"input": raw_args}

            with metrics.timer("agent_loop_tool", labels={"tool": name}):
                packed = await harness.execute(
                    name,
                    params,
                    tool_call_id=tc.get("id"),
                    ctx=tool_ctx,
                )
            history.append(packed)
            metrics.inc("tool_calls_total", labels={"tool": name, "success": str(bool(packed.get("success")))})

            # Deferred Tool Loading：tool_search 激活的工具并入本轮 tools[]
            try:
                from utils.agent_infra.disclosure import activate_tools_from_result
                from utils.agent_tools.registry import get_agent_tool_registry

                allow_write = bool(getattr(tool_ctx, "allow_write", False)) if tool_ctx else False
                activated = None
                if tool_ctx is not None:
                    md = getattr(tool_ctx, "metadata", None) or {}
                    activated = set(md.get("activated_tools") or [])
                tools = activate_tools_from_result(
                    tools or [],
                    packed,
                    get_agent_tool_registry(),
                    activated=activated,
                    allow_write=allow_write,
                )
                if tool_ctx is not None and activated is not None:
                    tool_ctx.metadata["activated_tools"] = sorted(activated)
            except Exception as e:
                logger.debug("deferred tool activate soft-fail: %s", e)

            if on_step:
                await on_step(
                    {
                        "type": "tool",
                        "step": step,
                        "tool_name": name,
                        "result": packed,
                        "trace_id": tid,
                    }
                )

            # 首次写入即定稿截断——后续 turn replay 同一字节，避免打爆 cache
            raw_tool_text = packed.get("llm_text") or packed.get("error") or ""
            tool_text = _clamp_tool_text(str(raw_tool_text), tool_result_max)
            msgs.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.get("id") or packed.get("tool_call_id"),
                    "content": tool_text,
                    "_content_finalized": True,
                }
            )

        if checkpoint_store and checkpoint_id:
            await checkpoint_store.save(
                checkpoint_id,
                {
                    "messages": msgs,
                    "step": step,
                    "tool_history": history,
                    "trace_id": tid,
                    "status": "running",
                },
            )
        if substrate and wl_id:
            try:
                await substrate.checkpoint(
                    wl_id,
                    messages=msgs,
                    step=step,
                    tool_history=history,
                    status="running",
                    trace_id=tid,
                )
            except Exception as e:
                logger.debug("substrate mid checkpoint: %s", e)

    # max steps — Harness 决定挂起；Substrate 执行机制
    final_content = final_content or (msgs[-1].get("content") if msgs else "") or ""
    if substrate and wl_id:
        try:
            await substrate.checkpoint(
                wl_id,
                messages=msgs,
                step=max_steps,
                tool_history=history,
                status="suspended",
                trace_id=tid,
            )
            await substrate.suspend(wl_id, reason="max_steps")
        except Exception as e:
            logger.debug("substrate suspend on max_steps: %s", e)
    return AgentLoopResult(
        content=str(final_content or ""),
        messages=msgs,
        tool_history=history,
        steps=max_steps,
        finish_reason="max_steps",
        trace_id=tid,
    )
