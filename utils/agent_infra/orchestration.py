"""
调度与多 Agent 编排 — DAG、Handoff、Reviewer Gate、HITL
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class NodeStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class HandoffSpec:
    """结构化 Agent 交接：所有权 + 上下文引用。"""

    from_agent: str
    to_agent: str
    payload_ref: str = ""  # artifact / checkpoint / memory key
    reason: str = ""
    context_keys: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "payload_ref": self.payload_ref,
            "reason": self.reason,
            "context_keys": self.context_keys,
        }


@dataclass
class ApprovalGate:
    """Human-in-the-loop 审批门。"""

    gate_id: str
    node_id: str
    status: str = "pending"  # pending | approved | rejected | edited
    comment: str = ""
    edited_payload: Optional[Dict[str, Any]] = None
    decided_by: Optional[str] = None
    decided_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "node_id": self.node_id,
            "status": self.status,
            "comment": self.comment,
            "edited_payload": self.edited_payload,
            "decided_by": self.decided_by,
            "decided_at": self.decided_at,
        }


@dataclass
class OrchestrationNode:
    node_id: str
    agent_id: str
    title: str = ""
    depends_on: List[str] = field(default_factory=list)
    is_reviewer: bool = False
    requires_approval: bool = False
    status: NodeStatus = NodeStatus.PENDING
    handoff: Optional[HandoffSpec] = None
    artifact_ref: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "agent_id": self.agent_id,
            "title": self.title,
            "depends_on": self.depends_on,
            "is_reviewer": self.is_reviewer,
            "requires_approval": self.requires_approval,
            "status": self.status.value if isinstance(self.status, NodeStatus) else self.status,
            "handoff": self.handoff.to_dict() if self.handoff else None,
            "artifact_ref": self.artifact_ref,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class OrchestrationPlan:
    plan_id: str
    nodes: List[OrchestrationNode] = field(default_factory=list)
    gates: Dict[str, ApprovalGate] = field(default_factory=dict)
    status: str = "ready"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "nodes": [n.to_dict() for n in self.nodes],
            "gates": {k: g.to_dict() for k, g in self.gates.items()},
            "status": self.status,
            "created_at": self.created_at,
        }


class DAGScheduler:
    """根据 depends_on 计算就绪集；支持 reviewer 门禁与审批。"""

    def __init__(self, plan: OrchestrationPlan) -> None:
        self.plan = plan
        self._index = {n.node_id: n for n in plan.nodes}

    def validate(self) -> List[str]:
        errors: List[str] = []
        ids = set(self._index)
        for n in self.plan.nodes:
            for dep in n.depends_on:
                if dep not in ids:
                    errors.append(f"{n.node_id} depends on missing node {dep}")
        # 简单环检测
        visiting: Set[str] = set()
        visited: Set[str] = set()

        def dfs(nid: str) -> bool:
            if nid in visiting:
                return True
            if nid in visited:
                return False
            visiting.add(nid)
            node = self._index[nid]
            for dep in node.depends_on:
                if dfs(dep):
                    return True
            visiting.remove(nid)
            visited.add(nid)
            return False

        for nid in ids:
            if dfs(nid):
                errors.append(f"cycle detected involving {nid}")
                break
        return errors

    def ready_nodes(self) -> List[OrchestrationNode]:
        ready: List[OrchestrationNode] = []
        for n in self.plan.nodes:
            if n.status not in (NodeStatus.PENDING, NodeStatus.READY):
                continue
            deps_ok = True
            for d in n.depends_on:
                dep = self._index[d]
                if dep.requires_approval:
                    if dep.status not in (NodeStatus.APPROVED, NodeStatus.DONE):
                        deps_ok = False
                        break
                elif dep.status != NodeStatus.DONE:
                    deps_ok = False
                    break
            if deps_ok:
                n.status = NodeStatus.READY
                ready.append(n)
        return ready

    def mark_running(self, node_id: str) -> OrchestrationNode:
        n = self._index[node_id]
        n.status = NodeStatus.RUNNING
        return n

    def mark_done(self, node_id: str, *, artifact_ref: Optional[str] = None) -> OrchestrationNode:
        n = self._index[node_id]
        n.artifact_ref = artifact_ref or n.artifact_ref
        if n.requires_approval:
            n.status = NodeStatus.WAITING_APPROVAL
            gate = ApprovalGate(
                gate_id=f"gate_{uuid.uuid4().hex[:10]}",
                node_id=node_id,
            )
            self.plan.gates[gate.gate_id] = gate
        else:
            n.status = NodeStatus.DONE
        return n

    def mark_failed(self, node_id: str, error: str) -> OrchestrationNode:
        n = self._index[node_id]
        n.status = NodeStatus.FAILED
        n.error = error
        return n

    def decide_gate(
        self,
        gate_id: str,
        *,
        approve: bool,
        comment: str = "",
        edited_payload: Optional[Dict[str, Any]] = None,
        decided_by: Optional[str] = None,
    ) -> ApprovalGate:
        gate = self.plan.gates[gate_id]
        gate.status = "approved" if approve else "rejected"
        if edited_payload is not None:
            gate.status = "edited"
            gate.edited_payload = edited_payload
        gate.comment = comment
        gate.decided_by = decided_by
        gate.decided_at = datetime.now().isoformat()
        node = self._index[gate.node_id]
        if gate.status in ("approved", "edited"):
            node.status = NodeStatus.DONE if not node.is_reviewer else NodeStatus.DONE
            # 若 edited，把内容塞进 metadata
            if edited_payload is not None:
                node.metadata["edited_payload"] = edited_payload
        else:
            node.status = NodeStatus.REJECTED
        return gate

    def is_complete(self) -> bool:
        terminal = {
            NodeStatus.DONE,
            NodeStatus.SKIPPED,
            NodeStatus.REJECTED,
            NodeStatus.FAILED,
        }
        return all(n.status in terminal for n in self.plan.nodes)

    @staticmethod
    def from_linear_steps(
        steps: List[Dict[str, Any]],
        *,
        plan_id: Optional[str] = None,
        reviewer_agent_ids: Optional[Set[str]] = None,
    ) -> "DAGScheduler":
        """把线性步骤升级为链式 DAG（step_i depends_on step_{i-1}）。"""
        reviewer_agent_ids = reviewer_agent_ids or {"short_drama_evaluation"}
        nodes: List[OrchestrationNode] = []
        prev_id: Optional[str] = None
        for i, s in enumerate(steps):
            if not s.get("enabled", True):
                continue
            nid = s.get("id") or f"node_{i + 1}"
            agent_id = s.get("agent_id") or ""
            node = OrchestrationNode(
                node_id=nid,
                agent_id=agent_id,
                title=s.get("title") or agent_id,
                depends_on=[prev_id] if prev_id else list(s.get("depends_on") or []),
                is_reviewer=agent_id in reviewer_agent_ids or bool(s.get("is_reviewer")),
                requires_approval=bool(s.get("requires_approval", False)),
            )
            # 显式 depends_on 优先
            if s.get("depends_on"):
                node.depends_on = list(s["depends_on"])
            nodes.append(node)
            prev_id = nid
        plan = OrchestrationPlan(plan_id=plan_id or f"plan_{uuid.uuid4().hex[:10]}", nodes=nodes)
        return DAGScheduler(plan)
