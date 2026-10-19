"""
SubagentRunner — Agent-as-tool：父 Agent 保留对用户回复的所有权。

借鉴 OpenAI as_tool / Claude Subagents：上下文隔离、深度限额、独立 checkpoint。
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

DEFAULT_MAX_DEPTH = 2
DEFAULT_MAX_PARALLEL = 3
DEFAULT_TIMEOUT_S = 120

# 命名归一化统一入口（避免多处各自维护别名表）
from utils.agent_runtime import normalize_agent_id  # noqa: E402


@dataclass
class SubagentSpec:
    agent_id: str
    task: str
    context_keys: List[str] = field(default_factory=list)
    timeout: float = DEFAULT_TIMEOUT_S
    max_depth: int = DEFAULT_MAX_DEPTH
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "task": self.task,
            "context_keys": self.context_keys,
            "timeout": self.timeout,
            "max_depth": self.max_depth,
            "metadata": self.metadata,
        }


@dataclass
class SubagentResult:
    success: bool
    agent_id: str
    content: str = ""
    error: Optional[str] = None
    checkpoint_id: Optional[str] = None
    events: List[Dict[str, Any]] = field(default_factory=list)
    duration_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "agent_id": self.agent_id,
            "content": self.content,
            "error": self.error,
            "checkpoint_id": self.checkpoint_id,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
            "event_count": len(self.events),
        }

    def to_llm_text(self) -> str:
        if not self.success:
            return f"[subagent {self.agent_id} failed] {self.error or 'unknown error'}"
        body = self.content.strip() or "(empty)"
        return f"[subagent {self.agent_id} result]\n{body}"


def _clip_context(
    context: Optional[Dict[str, Any]],
    keys: Optional[List[str]],
) -> Dict[str, Any]:
    ctx = dict(context or {})
    always = {"user_id", "session_id", "drama_id", "project_id"}
    if not keys:
        # 默认只传核心键，避免把父 transcript 整包塞进子 Agent
        return {k: ctx[k] for k in always if k in ctx}
    allow = set(keys) | always
    return {k: v for k, v in ctx.items() if k in allow}


def _load_agent_instance(agent_id: str) -> Any:
    from utils.agent_runtime import load_agent

    return load_agent(normalize_agent_id(agent_id), fresh=True)


class SubagentRunner:
    """统一 spawn：加载 → 裁剪 context → 跑 process_request → 聚合结果。"""

    def __init__(
        self,
        *,
        max_depth: int = DEFAULT_MAX_DEPTH,
        max_parallel: int = DEFAULT_MAX_PARALLEL,
        allowed_subagents: Optional[Set[str]] = None,
    ) -> None:
        self.max_depth = max_depth
        self.max_parallel = max_parallel
        self.allowed_subagents = allowed_subagents
        self._sem = asyncio.Semaphore(max_parallel)

    def _check_allow(self, agent_id: str, parent_allowed: Optional[Set[str]]) -> Optional[str]:
        aid = normalize_agent_id(agent_id)
        allow = parent_allowed if parent_allowed is not None else self.allowed_subagents
        if allow is not None and aid not in allow and agent_id not in allow:
            return f"agent '{aid}' not in allowed_subagents"
        return None

    async def spawn(
        self,
        spec: SubagentSpec,
        *,
        parent_agent_id: str = "",
        context: Optional[Dict[str, Any]] = None,
        depth: int = 0,
        allowed_subagents: Optional[Set[str]] = None,
        on_event: Optional[Callable[[Dict[str, Any]], Any]] = None,
    ) -> SubagentResult:
        started = datetime.now()
        agent_id = normalize_agent_id(spec.agent_id)
        depth_limit = min(spec.max_depth, self.max_depth)

        if depth >= depth_limit:
            return SubagentResult(
                success=False,
                agent_id=agent_id,
                error=f"subagent depth limit exceeded ({depth_limit})",
            )

        deny = self._check_allow(agent_id, allowed_subagents)
        if deny:
            return SubagentResult(success=False, agent_id=agent_id, error=deny)

        child_ctx = _clip_context(context, spec.context_keys)
        child_ctx["parent_agent"] = parent_agent_id or child_ctx.get("parent_agent") or "unknown"
        child_ctx["tool_call"] = True
        child_ctx["subagent"] = True
        child_ctx["subagent_depth"] = depth + 1
        checkpoint_id = f"sub_{uuid.uuid4().hex[:12]}_{agent_id}"
        child_ctx["checkpoint_id"] = checkpoint_id

        request_data = {
            "input": spec.task,
            "query": spec.task,
            "user_id": child_ctx.get("user_id", "default_user"),
            "session_id": child_ctx.get("session_id"),
            "drama_id": child_ctx.get("drama_id"),
            "project_id": child_ctx.get("project_id"),
            "stream_mode": True,
        }

        events: List[Dict[str, Any]] = []
        chunks: List[str] = []

        async with self._sem:
            try:
                agent = _load_agent_instance(agent_id)
            except Exception as e:
                logger.exception("load subagent failed: %s", agent_id)
                return SubagentResult(success=False, agent_id=agent_id, error=str(e))

            async def _consume() -> None:
                from utils.agent_dispatch import build_agent_generator

                async for event in build_agent_generator(agent, request_data, child_ctx):
                    if not isinstance(event, dict):
                        continue
                    events.append(event)
                    et = event.get("event_type") or event.get("type")
                    data = event.get("data")
                    # 兼容多种「最终内容」事件类型：llm_chunk/message/content/final_result
                    if et in ("llm_chunk", "message", "content", "final_result") and isinstance(data, str):
                        chunks.append(data)
                    elif et == "complete" and isinstance(data, dict):
                        content = data.get("content")
                        if content and not chunks:
                            chunks.append(str(content))
                    if on_event:
                        maybe = on_event(event)
                        if asyncio.iscoroutine(maybe):
                            await maybe

            try:
                await asyncio.wait_for(_consume(), timeout=float(spec.timeout or DEFAULT_TIMEOUT_S))
            except asyncio.TimeoutError:
                return SubagentResult(
                    success=False,
                    agent_id=agent_id,
                    content="".join(chunks),
                    error=f"subagent timeout ({spec.timeout}s)",
                    checkpoint_id=checkpoint_id,
                    events=events,
                    duration_ms=int((datetime.now() - started).total_seconds() * 1000),
                )
            except Exception as e:
                logger.exception("subagent run failed: %s", agent_id)
                return SubagentResult(
                    success=False,
                    agent_id=agent_id,
                    content="".join(chunks),
                    error=str(e),
                    checkpoint_id=checkpoint_id,
                    events=events,
                    duration_ms=int((datetime.now() - started).total_seconds() * 1000),
                )

        content = "".join(chunks)
        return SubagentResult(
            success=True,
            agent_id=agent_id,
            content=content,
            checkpoint_id=checkpoint_id,
            events=events,
            duration_ms=int((datetime.now() - started).total_seconds() * 1000),
            metadata={"parent_agent": parent_agent_id, "depth": depth + 1},
        )

    async def spawn_many(
        self,
        specs: List[SubagentSpec],
        *,
        parent_agent_id: str = "",
        context: Optional[Dict[str, Any]] = None,
        depth: int = 0,
        allowed_subagents: Optional[Set[str]] = None,
        max_concurrency: int = 8,
    ) -> List[SubagentResult]:
        # 有界并发，避免一次 spawn 上百子代理放大请求打爆 LLM/资源
        sem = asyncio.Semaphore(max(1, max_concurrency))

        async def _bounded(s: SubagentSpec) -> SubagentResult:
            async with sem:
                return await self.spawn(
                    s,
                    parent_agent_id=parent_agent_id,
                    context=context,
                    depth=depth,
                    allowed_subagents=allowed_subagents,
                )

        return list(await asyncio.gather(*(_bounded(s) for s in specs)))


def make_subagent_event(
    event_type: str,
    data: Any,
    *,
    agent_source: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "event_type": event_type,
        "agent_source": agent_source,
        "timestamp": datetime.now().isoformat(),
        "data": data,
        "metadata": metadata or {},
    }


async def iter_spawn_events(
    runner: SubagentRunner,
    spec: SubagentSpec,
    *,
    parent_agent_id: str = "",
    context: Optional[Dict[str, Any]] = None,
    depth: int = 0,
    allowed_subagents: Optional[Set[str]] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """边跑边 yield subagent_start / 子事件 / subagent_end。"""
    aid = normalize_agent_id(spec.agent_id)
    yield make_subagent_event(
        "subagent_start",
        {"agent_id": aid, "task": spec.task[:200]},
        agent_source=parent_agent_id,
        metadata={"agent_id": aid},
    )

    queue: asyncio.Queue = asyncio.Queue()

    async def _on_event(ev: Dict[str, Any]) -> None:
        await queue.put(ev)

    async def _run() -> SubagentResult:
        try:
            return await runner.spawn(
                spec,
                parent_agent_id=parent_agent_id,
                context=context,
                depth=depth,
                allowed_subagents=allowed_subagents,
                on_event=_on_event,
            )
        finally:
            await queue.put(None)

    task = asyncio.create_task(_run())
    while True:
        item = await queue.get()
        if item is None:
            break
        # 透传时标注来自子 Agent
        meta = dict(item.get("metadata") or {})
        meta["from_subagent"] = aid
        item = {**item, "metadata": meta}
        yield item

    result = await task
    yield make_subagent_event(
        "subagent_end",
        result.to_dict(),
        agent_source=parent_agent_id,
        metadata={"agent_id": aid, "success": result.success},
    )
