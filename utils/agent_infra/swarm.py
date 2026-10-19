"""
SwarmRunner — 按需组合多个专家（parallel / pipeline / dag）。

复用 DAGScheduler，不实现 peer 自由辩论 GroupChat。
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set

from .orchestration import DAGScheduler, NodeStatus, OrchestrationNode, OrchestrationPlan
from .subagents import SubagentResult, SubagentRunner, SubagentSpec, normalize_agent_id

logger = logging.getLogger(__name__)


@dataclass
class CompositionNode:
    node_id: str
    agent_id: str
    task: str = ""
    depends_on: List[str] = field(default_factory=list)
    title: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "agent_id": self.agent_id,
            "task": self.task,
            "depends_on": self.depends_on,
            "title": self.title,
        }


@dataclass
class CompositionPlan:
    """LLM / 调用方可构造的组合计划。"""

    nodes: List[CompositionNode] = field(default_factory=list)
    mode: str = "dag"  # parallel | pipeline | dag
    plan_id: str = ""
    shared_task: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "mode": self.mode,
            "shared_task": self.shared_task,
            "nodes": [n.to_dict() for n in self.nodes],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CompositionPlan":
        raw_nodes = data.get("nodes") or []
        nodes: List[CompositionNode] = []
        for i, n in enumerate(raw_nodes):
            if isinstance(n, str):
                nodes.append(
                    CompositionNode(
                        node_id=f"n{i + 1}",
                        agent_id=normalize_agent_id(n),
                        task=str(data.get("shared_task") or data.get("task") or ""),
                    )
                )
            elif isinstance(n, dict):
                nodes.append(
                    CompositionNode(
                        node_id=str(n.get("node_id") or n.get("id") or f"n{i + 1}"),
                        agent_id=normalize_agent_id(str(n.get("agent_id") or n.get("agent") or "")),
                        task=str(n.get("task") or data.get("shared_task") or data.get("task") or ""),
                        depends_on=list(n.get("depends_on") or []),
                        title=str(n.get("title") or ""),
                    )
                )
        mode = str(data.get("mode") or "dag").lower()
        plan = cls(
            nodes=nodes,
            mode=mode,
            plan_id=str(data.get("plan_id") or f"compose_{uuid.uuid4().hex[:10]}"),
            shared_task=str(data.get("shared_task") or data.get("task") or ""),
        )
        plan._normalize_mode()
        return plan

    def _normalize_mode(self) -> None:
        if self.mode == "parallel":
            for n in self.nodes:
                n.depends_on = []
        elif self.mode == "pipeline":
            prev: Optional[str] = None
            for n in self.nodes:
                n.depends_on = [prev] if prev else []
                prev = n.node_id
        # dag: keep explicit depends_on


@dataclass
class CompositionResult:
    success: bool
    plan_id: str
    results: Dict[str, SubagentResult] = field(default_factory=dict)
    summary: str = ""
    error: Optional[str] = None
    duration_ms: int = 0
    blackboard: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "plan_id": self.plan_id,
            "summary": self.summary,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "results": {k: v.to_dict() for k, v in self.results.items()},
            "blackboard": self.blackboard,
        }

    def to_llm_text(self) -> str:
        if not self.success and not self.results:
            return f"[composition failed] {self.error or 'unknown'}"
        parts = [f"[composition {self.plan_id}]"]
        for nid, r in self.results.items():
            status = "ok" if r.success else "fail"
            parts.append(f"## {nid} ({r.agent_id}) [{status}]\n{r.content or r.error or ''}")
        if self.summary:
            parts.append(f"## summary\n{self.summary}")
        return "\n\n".join(parts)


class SwarmRunner:
    def __init__(
        self,
        *,
        subagent_runner: Optional[SubagentRunner] = None,
        max_parallel: int = 3,
    ) -> None:
        self.subagent_runner = subagent_runner or SubagentRunner(max_parallel=max_parallel)
        self.max_parallel = max_parallel

    def _to_orchestration_plan(self, plan: CompositionPlan) -> OrchestrationPlan:
        nodes = [
            OrchestrationNode(
                node_id=n.node_id,
                agent_id=n.agent_id,
                title=n.title or n.agent_id,
                depends_on=list(n.depends_on),
                metadata={"task": n.task or plan.shared_task},
            )
            for n in plan.nodes
            if n.agent_id
        ]
        return OrchestrationPlan(plan_id=plan.plan_id or f"compose_{uuid.uuid4().hex[:10]}", nodes=nodes)

    async def run(
        self,
        plan: CompositionPlan,
        *,
        parent_agent_id: str = "",
        context: Optional[Dict[str, Any]] = None,
        blackboard: Optional[Dict[str, Any]] = None,
        allowed_subagents: Optional[Set[str]] = None,
        depth: int = 0,
        on_node_done: Optional[Callable[[str, SubagentResult], Awaitable[None]]] = None,
    ) -> CompositionResult:
        started = datetime.now()
        plan._normalize_mode()
        if not plan.nodes:
            return CompositionResult(
                success=False,
                plan_id=plan.plan_id or "",
                error="empty composition plan",
            )

        orch = self._to_orchestration_plan(plan)
        scheduler = DAGScheduler(orch)
        errors = scheduler.validate()
        if errors:
            return CompositionResult(
                success=False,
                plan_id=orch.plan_id,
                error="; ".join(errors),
            )

        board: Dict[str, Any] = dict(blackboard or {})
        results: Dict[str, SubagentResult] = {}
        task_by_id = {n.node_id: (n.task or plan.shared_task) for n in plan.nodes}

        while not scheduler.is_complete():
            ready = scheduler.ready_nodes()
            if not ready:
                # 死锁 / 全失败
                pending = [n for n in orch.nodes if n.status in (NodeStatus.PENDING, NodeStatus.READY)]
                if pending:
                    for n in pending:
                        scheduler.mark_failed(n.node_id, "no ready nodes (dependency failure)")
                break

            async def _run_node(node: OrchestrationNode) -> None:
                scheduler.mark_running(node.node_id)
                # 把已完成节点结果注入任务描述（轻量黑板）
                prior = ""
                if board:
                    snippets = []
                    for dep in node.depends_on:
                        if dep in board:
                            snippets.append(f"[{dep}]: {str(board[dep])[:1500]}")
                    if snippets:
                        prior = "\n\n--- prior outputs ---\n" + "\n".join(snippets)

                task_text = (task_by_id.get(node.node_id) or plan.shared_task or "") + prior
                spec = SubagentSpec(agent_id=node.agent_id, task=task_text)
                try:
                    result = await self.subagent_runner.spawn(
                        spec,
                        parent_agent_id=parent_agent_id,
                        context=context,
                        depth=depth,
                        allowed_subagents=allowed_subagents,
                    )
                except Exception as e:
                    result = SubagentResult(success=False, agent_id=node.agent_id, error=str(e))

                results[node.node_id] = result
                if result.success:
                    board[node.node_id] = result.content
                    scheduler.mark_done(node.node_id)
                else:
                    scheduler.mark_failed(node.node_id, result.error or "failed")

                if on_node_done:
                    await on_node_done(node.node_id, result)

            # 并行跑就绪集（受 max_parallel 约束已在 SubagentRunner）
            await asyncio.gather(*[_run_node(n) for n in ready])

        ok = all(r.success for r in results.values()) and bool(results)
        summary_parts = [
            f"{nid}/{r.agent_id}: {'ok' if r.success else 'fail'}"
            for nid, r in results.items()
        ]
        return CompositionResult(
            success=ok,
            plan_id=orch.plan_id,
            results=results,
            summary="; ".join(summary_parts),
            error=None if ok else "one or more agents failed",
            duration_ms=int((datetime.now() - started).total_seconds() * 1000),
            blackboard=board,
        )


def make_composition_event(
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
