"""
Agent Substrate — 沙箱工作负载生命周期与持久化

对齐文章分工:
  Harness Orchestrator  — 决定「何时」suspend / resume、上下文里放什么
  Agentic Infrastructure— 提供机制：隔离执行、checkpoint、空闲挂起、快照恢复

本模块是基础设施层：不关心业务 prompt，只管理 workload 状态机。
参考: Agent Substrate / OpenShell / K8s Agent Sandbox 思路
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .checkpoint import AgentCheckpoint, CheckpointStore

logger = logging.getLogger(__name__)

WORKLOAD_STATUSES = frozenset(
    {"pending", "running", "suspended", "completed", "failed", "aborted"}
)


@dataclass
class WorkloadSnapshot:
    """可恢复快照：消息 + 工具史 + 文件系统锚点（相对路径列表）。"""

    workload_id: str
    checkpoint_id: str
    status: str = "pending"
    session_id: Optional[str] = None
    agent_id: Optional[str] = None
    user_id: Optional[str] = None
    drama_id: Optional[str] = None
    sandbox_profile: str = "drama"  # readonly | drama | elevated
    messages: List[Dict[str, Any]] = field(default_factory=list)
    tool_history: List[Dict[str, Any]] = field(default_factory=list)
    step: int = 0
    trace_id: str = ""
    fs_anchors: List[str] = field(default_factory=list)  # 需保留的相对路径提示
    lease_owner: Optional[str] = None
    suspended_at: Optional[str] = None
    resumed_at: Optional[str] = None
    idle_timeout_s: int = 900
    metadata: Dict[str, Any] = field(default_factory=dict)
    updated_at: str = ""
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["updated_at"] = self.updated_at or datetime.now().isoformat()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkloadSnapshot":
        known = cls.__dataclass_fields__
        return cls(**{k: v for k, v in data.items() if k in known})


class AgentSubstrate:
    """
    管理多个 harness 共享的执行基底:
    - checkpoint 持久化
    - suspend / resume
    - 空闲回收（释放「算力槽位」语义，文件快照保留）
    """

    def __init__(
        self,
        *,
        checkpoint_store: Optional[CheckpointStore] = None,
        root: Optional[str] = None,
        idle_timeout_s: int = 900,
    ):
        self.checkpoints = checkpoint_store or CheckpointStore()
        self.root = Path(root or "data/agent_workloads")
        self.root.mkdir(parents=True, exist_ok=True)
        self.idle_timeout_s = idle_timeout_s
        self._active: Dict[str, WorkloadSnapshot] = {}

    def _path(self, workload_id: str) -> Path:
        safe = workload_id.replace("/", "_").replace("..", "_")
        return self.root / f"{safe}.json"

    async def _persist(self, snap: WorkloadSnapshot) -> WorkloadSnapshot:
        import json

        import aiofiles

        snap.updated_at = datetime.now().isoformat()
        path = self._path(snap.workload_id)
        async with aiofiles.open(path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(snap.to_dict(), ensure_ascii=False, indent=2))
        self._active[snap.workload_id] = snap
        return snap

    async def load(self, workload_id: str) -> Optional[WorkloadSnapshot]:
        import json

        import aiofiles

        if workload_id in self._active:
            return self._active[workload_id]
        path = self._path(workload_id)
        if not path.exists():
            return None
        try:
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                data = json.loads(await f.read())
            snap = WorkloadSnapshot.from_dict(data)
            self._active[workload_id] = snap
            return snap
        except Exception:
            logger.exception("load workload failed: %s", workload_id)
            return None

    async def create_workload(
        self,
        *,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        user_id: Optional[str] = None,
        drama_id: Optional[str] = None,
        sandbox_profile: str = "drama",
        messages: Optional[List[Dict[str, Any]]] = None,
        idle_timeout_s: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        workload_id: Optional[str] = None,
    ) -> WorkloadSnapshot:
        wid = workload_id or f"wl_{uuid.uuid4().hex[:12]}"
        cpid = f"cp_{wid}"
        now = datetime.now().isoformat()
        snap = WorkloadSnapshot(
            workload_id=wid,
            checkpoint_id=cpid,
            status="pending",
            session_id=session_id,
            agent_id=agent_id,
            user_id=user_id,
            drama_id=drama_id,
            sandbox_profile=sandbox_profile,
            messages=list(messages or []),
            idle_timeout_s=idle_timeout_s or self.idle_timeout_s,
            metadata=dict(metadata or {}),
            created_at=now,
            updated_at=now,
            fs_anchors=_default_fs_anchors(drama_id),
        )
        await self.checkpoints.save(
            cpid,
            {
                "messages": snap.messages,
                "step": 0,
                "status": "running",
                "session_id": session_id,
                "agent_id": agent_id,
                "metadata": {"workload_id": wid, "sandbox_profile": sandbox_profile},
            },
        )
        snap.status = "running"
        return await self._persist(snap)

    async def checkpoint(
        self,
        workload_id: str,
        *,
        messages: List[Dict[str, Any]],
        step: int,
        tool_history: Optional[List[Dict[str, Any]]] = None,
        status: str = "running",
        trace_id: str = "",
    ) -> WorkloadSnapshot:
        """Harness 每步调用：基础设施落盘。"""
        snap = await self.load(workload_id)
        if not snap:
            raise KeyError(f"workload not found: {workload_id}")
        snap.messages = list(messages)
        snap.step = step
        snap.tool_history = list(tool_history or snap.tool_history)
        snap.trace_id = trace_id or snap.trace_id
        if status in WORKLOAD_STATUSES:
            snap.status = status
        await self.checkpoints.save(
            snap.checkpoint_id,
            {
                "messages": snap.messages,
                "step": snap.step,
                "tool_history": snap.tool_history,
                "trace_id": snap.trace_id,
                "status": "running" if status == "running" else status,
                "session_id": snap.session_id,
                "agent_id": snap.agent_id,
                "metadata": {"workload_id": workload_id},
            },
        )
        return await self._persist(snap)

    async def suspend(self, workload_id: str, *, reason: str = "idle") -> WorkloadSnapshot:
        """
        挂起：释放「活跃执行槽」，保留 checkpoint + 快照。
        Harness 决定何时调用；本方法只做机制。
        """
        snap = await self.load(workload_id)
        if not snap:
            raise KeyError(f"workload not found: {workload_id}")
        if snap.status in ("completed", "failed", "aborted"):
            return snap
        snap.status = "suspended"
        snap.suspended_at = datetime.now().isoformat()
        snap.metadata["suspend_reason"] = reason
        snap.lease_owner = None
        await self.checkpoints.save(
            snap.checkpoint_id,
            {
                "messages": snap.messages,
                "step": snap.step,
                "tool_history": snap.tool_history,
                "trace_id": snap.trace_id,
                "status": "aborted",  # checkpoint 语义：非活跃
                "metadata": {**(snap.metadata or {}), "suspended": True, "workload_id": workload_id},
            },
        )
        logger.info("substrate suspend %s reason=%s", workload_id, reason)
        return await self._persist(snap)

    async def resume(self, workload_id: str, *, owner: Optional[str] = None) -> WorkloadSnapshot:
        """恢复：加载 checkpoint，标记 running，供 Harness 继续 loop。"""
        snap = await self.load(workload_id)
        if not snap:
            raise KeyError(f"workload not found: {workload_id}")
        cp: Optional[AgentCheckpoint] = await self.checkpoints.load(snap.checkpoint_id)
        if cp:
            snap.messages = list(cp.messages or snap.messages)
            snap.step = int(cp.step or snap.step)
            snap.tool_history = list(cp.tool_history or snap.tool_history)
            snap.trace_id = cp.trace_id or snap.trace_id
        snap.status = "running"
        snap.resumed_at = datetime.now().isoformat()
        snap.lease_owner = owner or f"worker_{uuid.uuid4().hex[:8]}"
        snap.metadata.pop("suspend_reason", None)
        await self.checkpoints.save(
            snap.checkpoint_id,
            {
                "messages": snap.messages,
                "step": snap.step,
                "tool_history": snap.tool_history,
                "trace_id": snap.trace_id,
                "status": "running",
                "metadata": {"workload_id": workload_id, "resumed": True},
            },
        )
        logger.info("substrate resume %s owner=%s", workload_id, snap.lease_owner)
        return await self._persist(snap)

    def should_suspend(self, snap: WorkloadSnapshot, *, now: Optional[datetime] = None) -> bool:
        """
        Harness/调度器用的启发式：空闲超时且仍 running → 建议挂起。
        基础设施不主动改状态，只给建议。
        """
        if snap.status != "running":
            return False
        now = now or datetime.now()
        try:
            updated = datetime.fromisoformat(snap.updated_at) if snap.updated_at else now
        except Exception:
            updated = now
        return (now - updated) >= timedelta(seconds=snap.idle_timeout_s or self.idle_timeout_s)

    async def reclaim_idle(self, *, limit: int = 50) -> List[Dict[str, Any]]:
        """扫描本目录，挂起空闲 running workload。"""
        reclaimed: List[Dict[str, Any]] = []
        for path in list(self.root.glob("wl_*.json"))[: 500]:
            try:
                snap = await self.load(path.stem)
                if not snap:
                    continue
                if self.should_suspend(snap):
                    await self.suspend(snap.workload_id, reason="idle_reclaim")
                    reclaimed.append(
                        {"workload_id": snap.workload_id, "checkpoint_id": snap.checkpoint_id}
                    )
                    if len(reclaimed) >= limit:
                        break
            except Exception:
                logger.exception("reclaim failed %s", path)
        return reclaimed

    def sandbox_roots_for_profile(
        self,
        profile: str,
        *,
        drama_id: Optional[str] = None,
        workspace_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        """给 PathSandbox 的配置建议（Harness 创建沙箱时使用）。"""
        from utils.agent_tools.sandbox import (
            DEFAULT_READ_ROOTS,
            DEFAULT_WRITE_ROOTS,
            SandboxProfile,
        )

        return {
            "profile": profile,
            "drama_id": drama_id,
            "workspace_root": workspace_root,
            "read_roots": list(DEFAULT_READ_ROOTS),
            "write_roots": [] if profile == "readonly" else list(DEFAULT_WRITE_ROOTS),
            "sandbox_profile": SandboxProfile.READONLY
            if profile == "readonly"
            else SandboxProfile.ELEVATED
            if profile == "elevated"
            else SandboxProfile.DRAMA,
        }


def _default_fs_anchors(drama_id: Optional[str]) -> List[str]:
    if not drama_id:
        return ["projects/", "skills/"]
    return [
        f"projects/{drama_id}/",
        f"projects/{drama_id}/memory/",
        f"projects/{drama_id}/episodes/",
        "skills/",
    ]


_substrate: Optional[AgentSubstrate] = None


def get_agent_substrate() -> AgentSubstrate:
    global _substrate
    if _substrate is None:
        _substrate = AgentSubstrate()
    return _substrate
