"""
AgentTeam — 多智能体团队原语（对齐 Claude Code Agent Teams）

组成：
  - Lead：队长，负责规划/委派/最终合成（默认 juben_conductor，可换）
  - Teammates：专家 agent（SubagentRunner 隔离上下文、限深、限并发）
  - Shared Task List：task + depends_on（复用 DAGScheduler 做依赖追踪）
  - Blackboard：task 间共享产物（上游产出注入下游 prompt，最终可由 lead 合成）

复用（不重造轮子）：
  - SwarmRunner.run（DAG 调度 + 并行 spawn + 黑板注入 + on_node_done 回调）
  - SubagentRunner（spawn 单个专家）
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, List, Optional

from .subagents import SubagentResult, SubagentRunner, SubagentSpec, normalize_agent_id
from .swarm import CompositionNode, CompositionPlan, SwarmRunner

logger = logging.getLogger(__name__)

DEFAULT_LEAD_AGENT_ID = "juben_conductor"


@dataclass
class TeamTask:
    """团队任务清单里的一项（一个 teammate 的一次委派）。"""

    task_id: str
    agent_id: str
    title: str = ""
    prompt: str = ""
    depends_on: List[str] = field(default_factory=list)
    context_keys: List[str] = field(default_factory=list)
    is_reviewer: bool = False
    requires_approval: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], *, index: int = 0) -> "TeamTask":
        return cls(
            task_id=str(data.get("task_id") or data.get("id") or data.get("module") or f"task_{index + 1}"),
            agent_id=normalize_agent_id(str(data.get("agent_id") or "")),
            title=str(data.get("title") or ""),
            prompt=str(data.get("prompt") or data.get("rationale") or ""),
            depends_on=[str(d) for d in (data.get("depends_on") or [])],
            context_keys=[str(k) for k in (data.get("context_keys") or [])],
            is_reviewer=bool(data.get("is_reviewer", False)),
            requires_approval=bool(data.get("requires_approval", False)),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class TeamDefinition:
    """团队定义：lead + 任务清单。"""

    team_id: str
    lead_agent_id: str = DEFAULT_LEAD_AGENT_ID
    tasks: List[TeamTask] = field(default_factory=list)
    shared_task: str = ""
    synthesize: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TeamDefinition":
        raw_tasks = data.get("tasks") or data.get("members") or []
        tasks = [TeamTask.from_dict(t, index=i) for i, t in enumerate(raw_tasks)]
        return cls(
            team_id=str(data.get("team_id") or data.get("id") or "team"),
            lead_agent_id=normalize_agent_id(str(data.get("lead_agent_id") or DEFAULT_LEAD_AGENT_ID)),
            tasks=tasks,
            shared_task=str(data.get("shared_task") or data.get("task") or ""),
            synthesize=bool(data.get("synthesize", True)),
            metadata=dict(data.get("metadata") or {}),
        )

    def to_composition_plan(self) -> CompositionPlan:
        nodes = [
            CompositionNode(
                node_id=t.task_id,
                agent_id=t.agent_id,
                task=t.prompt or self.shared_task,
                depends_on=list(t.depends_on),
                title=t.title or t.agent_id,
            )
            for t in self.tasks
        ]
        plan = CompositionPlan(
            nodes=nodes,
            mode="dag",
            plan_id=self.team_id,
            shared_task=self.shared_task,
        )
        return plan


@dataclass
class TeamResult:
    team_id: str
    success: bool
    results: Dict[str, SubagentResult] = field(default_factory=dict)
    blackboard: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    synthesis: str = ""
    error: Optional[str] = None
    duration_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "team_id": self.team_id,
            "success": self.success,
            "summary": self.summary,
            "synthesis": self.synthesis,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "results": {k: v.to_dict() for k, v in self.results.items()},
            "blackboard": self.blackboard,
        }

    def to_llm_text(self) -> str:
        parts = [f"[team {self.team_id}] success={self.success}"]
        for tid, r in self.results.items():
            status = "ok" if r.success else "fail"
            parts.append(f"## {tid} ({r.agent_id}) [{status}]\n{r.content or r.error or ''}")
        if self.synthesis:
            parts.append(f"## lead synthesis\n{self.synthesis}")
        return "\n\n".join(parts)


class AgentTeam:
    """团队执行器：SwarmRunner 之上的轻量封装，补 lead 合成。"""

    def __init__(self, *, max_parallel: int = 3, subagent_runner: Optional[SubagentRunner] = None) -> None:
        self.swarm = SwarmRunner(
            subagent_runner=subagent_runner or SubagentRunner(max_parallel=max_parallel),
            max_parallel=max_parallel,
        )
        self.lead_agent_id = DEFAULT_LEAD_AGENT_ID

    async def run(
        self,
        team: TeamDefinition,
        *,
        context: Optional[Dict[str, Any]] = None,
        parent_agent_id: str = "",
        allowed_subagents: Optional[set] = None,
        depth: int = 0,
        on_task_done: Optional[Callable[[str, SubagentResult], Awaitable[None]]] = None,
    ) -> TeamResult:
        started = datetime.now()
        self.lead_agent_id = team.lead_agent_id or DEFAULT_LEAD_AGENT_ID

        if not team.tasks:
            return TeamResult(team_id=team.team_id, success=False, error="empty team (no tasks)")

        plan = team.to_composition_plan()
        comp = await self.swarm.run(
            plan,
            parent_agent_id=parent_agent_id,
            context=context,
            allowed_subagents=allowed_subagents,
            depth=depth,
            on_node_done=on_task_done,
        )

        synthesis = ""
        if team.synthesize and comp.blackboard:
            synthesis = await self._synthesize(team, comp.blackboard, context)

        return TeamResult(
            team_id=team.team_id,
            success=comp.success,
            results=comp.results,
            blackboard=comp.blackboard,
            summary=comp.summary,
            synthesis=synthesis,
            error=comp.error,
            duration_ms=int((datetime.now() - started).total_seconds() * 1000),
        )

    async def _synthesize(
        self,
        team: TeamDefinition,
        blackboard: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """让 lead 综合各 teammate 产出，输出一段简洁的团队结论。"""
        lead_id = team.lead_agent_id or DEFAULT_LEAD_AGENT_ID
        parts = [f"你是「{team.team_id}」团队的队长。以下为各专家（teammates）的产出，请综合成一段简明结论：\n"]
        for tid, content in blackboard.items():
            task = next((t for t in team.tasks if t.task_id == tid), None)
            label = task.title if task else tid
            parts.append(f"### {label} (`{tid}`)\n{str(content)[:3000]}\n")
        parts.append("请输出：1) 团队目标达成情况；2) 各产出的要点；3) 下一步建议。用中文。")

        runner = SubagentRunner(max_parallel=1)
        try:
            res = await runner.spawn(
                SubagentSpec(agent_id=lead_id, task="\n\n".join(parts)),
                parent_agent_id=lead_id,
                context=context,
            )
            return res.content.strip() if res.success else ""
        except Exception as e:
            logger.warning("team synthesis failed: %s", e)
            return ""


__all__ = [
    "TeamTask",
    "TeamDefinition",
    "TeamResult",
    "AgentTeam",
    "DEFAULT_LEAD_AGENT_ID",
]
