"""
Prompt Cache — OpenClaw / Pi 风格的前缀稳定与缓存边界

核心约定（对照 OpenClaw docs/reference/prompt-caching + Pi cachepoint/self-compact）：
1. system prompt 在 cache boundary 处拆成 stablePrefix / dynamicSuffix
2. 稳定内容保持跨 turn 字节级一致；易变内容一律落在边界下方
3. 工具列表按 name 排序，避免 discovery 顺序打爆前缀
4. OpenAI 兼容路由复用 session 级 prompt_cache_key
5. 归一化 usage → cacheRead / cacheWrite
"""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# 内部边界标记：组装时拆分，发往 provider 前可剥离（避免污染语义）
CACHE_BOUNDARY_MARKER = "\n<<<PROMPT_CACHE_BOUNDARY>>>\n"

# Anthropic / OpenAI-compat cache_control 形态
CACHE_RETENTION_NONE = "none"
CACHE_RETENTION_SHORT = "short"
CACHE_RETENTION_LONG = "long"


@dataclass
class PromptCacheConfig:
    """会话级 prompt-cache 策略。"""

    enabled: bool = True
    cache_retention: str = CACHE_RETENTION_SHORT  # none | short | long
    # OpenAI-compat：是否注入 prompt_cache_key
    supports_prompt_cache_key: bool = True
    # Anthropic-compat：是否在 system/tools 上打 ephemeral cache_control
    cache_control_format: Optional[str] = None  # None | "anthropic"
    # 工具结果截断上限（字节级近似）；已发送的结果不得再改写
    tool_result_max_chars: int = 8000
    # cache-ttl 剪枝：仅在 TTL 过期后修剪旧 tool results
    pruning_mode: str = "cache-ttl"  # off | always | cache-ttl
    pruning_ttl_seconds: float = 3600.0
    # 压缩：保留最近若干条 message（非 system）
    keep_recent_messages: int = 12
    # 压缩触发：history 字符超过该阈值
    compact_threshold_chars: int = 24000
    # 协议内预判式压缩（run_tool_loop 每步检查 should_compact）；受 compact_threshold_chars 门槛约束
    auto_compact: bool = True


@dataclass
class SystemPromptParts:
    """stable / dynamic 拆分结果。"""

    stable_prefix: str = ""
    dynamic_suffix: str = ""

    def join(self, *, include_marker: bool = True) -> str:
        stable = (self.stable_prefix or "").rstrip()
        dynamic = (self.dynamic_suffix or "").lstrip()
        if not dynamic:
            return stable
        if not stable:
            return dynamic
        if include_marker:
            return f"{stable}{CACHE_BOUNDARY_MARKER}{dynamic}"
        return f"{stable}\n\n{dynamic}"

    def to_system_messages(self, *, split_messages: bool = True) -> List[Dict[str, Any]]:
        """
        拆成两条 system message：稳定块可打 cache breakpoint，动态块不打。
        split_messages=False 时合并为单条（OpenAI Responses 风格 instructions）。
        """
        stable = (self.stable_prefix or "").strip()
        dynamic = (self.dynamic_suffix or "").strip()
        if not split_messages:
            text = self.join(include_marker=False)
            return [{"role": "system", "content": text}] if text else []
        out: List[Dict[str, Any]] = []
        if stable:
            out.append({"role": "system", "content": stable, "_cacheable": True})
        if dynamic:
            out.append({"role": "system", "content": dynamic, "_cacheable": False})
        return out


@dataclass
class CacheSessionState:
    """跟踪会话的 cache TTL / compaction 边界，供剪枝与 prompt_cache_key 使用。"""

    session_id: str
    last_cache_write_at: float = 0.0
    compaction_count: int = 0
    reset_count: int = 0
    last_prompt_fingerprint: str = ""

    def touch_cache_write(self) -> None:
        self.last_cache_write_at = time.time()

    def cache_ttl_expired(self, ttl_seconds: float) -> bool:
        if self.last_cache_write_at <= 0:
            return True
        return (time.time() - self.last_cache_write_at) >= ttl_seconds

    def prompt_cache_key(self, *, agent_id: str = "", model: str = "") -> str:
        """
        OpenClaw: session_id + reset + compaction boundary。
        保持跨 turn 稳定，直到 compaction / reset。
        """
        raw = f"{agent_id}|{self.session_id}|r{self.reset_count}|c{self.compaction_count}|{model}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


# 进程内会话 cache 状态
_CACHE_SESSIONS: Dict[str, CacheSessionState] = {}
_MAX_CACHE_SESSIONS = 10_000


def get_cache_session(session_id: str) -> CacheSessionState:
    sid = session_id or "default"
    state = _CACHE_SESSIONS.get(sid)
    if state is None:
        if len(_CACHE_SESSIONS) >= _MAX_CACHE_SESSIONS:
            # 淘汰最久未写的 session（LRU），防止无界增长
            oldest = min(
                _CACHE_SESSIONS.values(),
                key=lambda s: s.last_cache_write_at if s.last_cache_write_at > 0 else 0,
            )
            _CACHE_SESSIONS.pop(oldest.session_id, None)
        state = CacheSessionState(session_id=sid)
        _CACHE_SESSIONS[sid] = state
    return state


def normalize_prompt_text(text: str) -> str:
    """指纹归一化：统一换行与尾部空白，避免语义不变却打爆 cache。"""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fingerprint_prefix(stable_prefix: str, tools: Optional[List[Dict[str, Any]]] = None) -> str:
    tools_blob = ""
    if tools:
        names = []
        for t in tools:
            fn = t.get("function") or {}
            names.append(fn.get("name") or t.get("name") or "")
        tools_blob = ",".join(names)
    raw = normalize_prompt_text(stable_prefix) + "||" + tools_blob
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def sort_tools_for_cache(tools: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """OpenClaw: tools 按 name 排序，避免 listTools 顺序 churn。"""
    if not tools:
        return []
    def _name(t: Dict[str, Any]) -> str:
        fn = t.get("function") or {}
        return str(fn.get("name") or t.get("name") or "")
    return sorted(tools, key=_name)


def assemble_system_parts(
    *,
    system_prompt: str,
    stable_extra: Optional[List[str]] = None,
    dynamic_extra: Optional[List[str]] = None,
    prepend_system: str = "",
    append_system: str = "",
    prepend_dynamic_system: str = "",
    append_dynamic_system: str = "",
) -> SystemPromptParts:
    """
    组装 cache-aware system parts。

    稳定侧（上界）：system_prompt + prependSystemContext + appendSystemContext + stable_extra
    动态侧（下界）：memory / runtime / prependDynamicSystemContext / appendDynamicSystemContext
    """
    stable_blocks: List[str] = []
    if prepend_system and prepend_system.strip():
        stable_blocks.append(prepend_system.strip())
    if system_prompt and system_prompt.strip():
        stable_blocks.append(system_prompt.strip())
    for block in stable_extra or []:
        if block and str(block).strip():
            stable_blocks.append(str(block).strip())
    if append_system and append_system.strip():
        stable_blocks.append(append_system.strip())

    dynamic_blocks: List[str] = []
    if prepend_dynamic_system and prepend_dynamic_system.strip():
        dynamic_blocks.append(prepend_dynamic_system.strip())
    for block in dynamic_extra or []:
        if block and str(block).strip():
            dynamic_blocks.append(str(block).strip())
    if append_dynamic_system and append_dynamic_system.strip():
        dynamic_blocks.append(append_dynamic_system.strip())

    return SystemPromptParts(
        stable_prefix=normalize_prompt_text("\n\n".join(stable_blocks)),
        dynamic_suffix=normalize_prompt_text("\n\n".join(dynamic_blocks)),
    )


def strip_internal_fields(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """发送给 provider 前移除内部标记字段。"""
    cleaned: List[Dict[str, Any]] = []
    for m in messages:
        item = {k: v for k, v in m.items() if not str(k).startswith("_")}
        cleaned.append(item)
    return cleaned


def apply_anthropic_cache_markers(
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]],
    *,
    cache_retention: str = CACHE_RETENTION_SHORT,
) -> Tuple[List[Dict[str, Any]], Optional[List[Dict[str, Any]]]]:
    """
    对 OpenAI-compat + anthropic cache_control 路由：
    - 最后一个 cacheable system 块打 breakpoint
    - 最后一个 tool definition 打 breakpoint
    - 最近一条 user/tool 打 breakpoint
    """
    if cache_retention == CACHE_RETENTION_NONE:
        return strip_internal_fields(messages), tools

    ttl = "1h" if cache_retention == CACHE_RETENTION_LONG else None
    cache_ctrl: Dict[str, Any] = {"type": "ephemeral"}
    if ttl:
        cache_ctrl["ttl"] = ttl

    out_msgs: List[Dict[str, Any]] = []
    last_stable_idx = -1
    for i, m in enumerate(messages):
        if m.get("role") == "system" and m.get("_cacheable", True):
            last_stable_idx = i

    for i, m in enumerate(messages):
        item = {k: v for k, v in m.items() if not str(k).startswith("_")}
        if i == last_stable_idx and isinstance(item.get("content"), str):
            item["content"] = [
                {"type": "text", "text": item["content"], "cache_control": dict(cache_ctrl)}
            ]
        out_msgs.append(item)

    # 最近一条 user 或 tool
    for i in range(len(out_msgs) - 1, -1, -1):
        role = out_msgs[i].get("role")
        if role in ("user", "tool"):
            content = out_msgs[i].get("content")
            if isinstance(content, str) and content:
                out_msgs[i]["content"] = [
                    {"type": "text", "text": content, "cache_control": dict(cache_ctrl)}
                ]
            break

    marked_tools = tools
    if tools:
        marked_tools = [dict(t) for t in tools]
        last = marked_tools[-1]
        # OpenAI tools schema 顶层不支持 cache_control；部分 anthropic-compat 接受嵌套
        last["cache_control"] = dict(cache_ctrl)

    return out_msgs, marked_tools


def build_openai_cache_extra(
    *,
    session_id: str,
    agent_id: str = "",
    model: str = "",
    cache_retention: str = CACHE_RETENTION_SHORT,
    supports_prompt_cache_key: bool = True,
    config: Optional[PromptCacheConfig] = None,
) -> Dict[str, Any]:
    """构造传给 chat.completions 的 extra_body / 顶层字段。"""
    cfg = config or PromptCacheConfig(cache_retention=cache_retention)
    if not cfg.enabled or cache_retention == CACHE_RETENTION_NONE:
        return {}
    state = get_cache_session(session_id)
    extra: Dict[str, Any] = {}
    if supports_prompt_cache_key and cfg.supports_prompt_cache_key:
        extra["prompt_cache_key"] = state.prompt_cache_key(agent_id=agent_id, model=model)
    if cache_retention == CACHE_RETENTION_LONG:
        # OpenAI 延长保留（模型支持时）；不支持的 provider 应忽略
        extra["prompt_cache_retention"] = "24h"
    return extra


def normalize_cache_usage(usage: Optional[Dict[str, Any]]) -> Dict[str, int]:
    """归一化各家 usage → cacheRead / cacheWrite。"""
    usage = usage or {}
    cache_read = 0
    cache_write = 0

    # 顶层
    cache_read = int(
        usage.get("cache_read")
        or usage.get("cacheRead")
        or usage.get("cached_tokens")
        or usage.get("prompt_cache_hit_tokens")  # DeepSeek 自动前缀缓存
        or usage.get("prefix_hit_tokens")
        or 0
    )
    cache_write = int(
        usage.get("cache_write")
        or usage.get("cacheWrite")
        or usage.get("cache_creation_input_tokens")
        or usage.get("prompt_cache_miss_tokens")  # DeepSeek 自动前缀缓存
        or usage.get("prefix_miss_tokens")
        or 0
    )

    # OpenAI nested
    ptd = usage.get("prompt_tokens_details") or usage.get("input_tokens_details") or {}
    if isinstance(ptd, dict):
        cache_read = cache_read or int(ptd.get("cached_tokens") or 0)
        cache_write = cache_write or int(ptd.get("cache_write_tokens") or 0)

    # Anthropic
    cache_read = cache_read or int(usage.get("cache_read_input_tokens") or 0)
    cache_write = cache_write or int(usage.get("cache_creation_input_tokens") or 0)

    return {
        "cacheRead": cache_read,
        "cacheWrite": cache_write,
        "prompt_tokens": int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
        "completion_tokens": int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
        "total_tokens": int(usage.get("total_tokens") or 0),
    }


def clamp_tool_result_text(text: str, max_chars: int) -> str:
    """首次写入即截断；后续 replay 必须复用同一文本，禁止再改。"""
    if not text or max_chars <= 0 or len(text) <= max_chars:
        return text or ""
    keep = max(0, max_chars - 24)
    return text[:keep] + "\n...[tool result truncated]..."


@dataclass
class AssembledPrompt:
    """一次 turn 的可发送消息 + cache 元数据。"""

    messages: List[Dict[str, Any]]
    parts: SystemPromptParts
    prompt_cache_key: str = ""
    prefix_fingerprint: str = ""
    extra_body: Dict[str, Any] = field(default_factory=dict)
    compaction_applied: bool = False
    pruning_applied: bool = False


def load_prompt_cache_config() -> PromptCacheConfig:
    """从 config.yaml `prompt_cache` 段加载；缺失则用默认。"""
    try:
        from config.settings import load_yaml_config

        raw = (load_yaml_config() or {}).get("prompt_cache") or {}
        if not isinstance(raw, dict):
            return PromptCacheConfig()
        return PromptCacheConfig(
            enabled=bool(raw.get("enabled", True)),
            cache_retention=str(raw.get("cache_retention") or CACHE_RETENTION_SHORT),
            supports_prompt_cache_key=bool(raw.get("supports_prompt_cache_key", True)),
            cache_control_format=raw.get("cache_control_format"),
            tool_result_max_chars=int(raw.get("tool_result_max_chars") or 8000),
            pruning_mode=str(raw.get("pruning_mode") or "cache-ttl"),
            pruning_ttl_seconds=float(raw.get("pruning_ttl_seconds") or 3600),
            keep_recent_messages=int(raw.get("keep_recent_messages") or 12),
            compact_threshold_chars=int(raw.get("compact_threshold_chars") or 24000),
            auto_compact=bool(raw.get("auto_compact", True)),
        )
    except Exception:
        return PromptCacheConfig()
