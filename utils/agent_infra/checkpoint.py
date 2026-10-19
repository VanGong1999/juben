"""
Agent Checkpoint — 步级状态持久化，支持 Resume

存储：data/agent_checkpoints/{id}.json（默认可换 Redis）
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles

from utils.atomic_write import atomic_write_text, atomic_write_text_async, FileLock

logger = logging.getLogger(__name__)


@dataclass
class AgentCheckpoint:
    checkpoint_id: str
    messages: List[Dict[str, Any]] = field(default_factory=list)
    step: int = 0
    tool_history: List[Dict[str, Any]] = field(default_factory=list)
    trace_id: str = ""
    status: str = "running"  # running | completed | failed | aborted
    session_id: Optional[str] = None
    agent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["updated_at"] = self.updated_at or datetime.now().isoformat()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentCheckpoint":
        return cls(
            checkpoint_id=data["checkpoint_id"],
            messages=list(data.get("messages") or []),
            step=int(data.get("step") or 0),
            tool_history=list(data.get("tool_history") or []),
            trace_id=data.get("trace_id") or "",
            status=data.get("status") or "running",
            session_id=data.get("session_id"),
            agent_id=data.get("agent_id"),
            metadata=dict(data.get("metadata") or {}),
            updated_at=data.get("updated_at") or "",
        )


class CheckpointStore:
    def __init__(self, root: Optional[str] = None) -> None:
        self.root = Path(root or "data/agent_checkpoints")
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, checkpoint_id: str) -> Path:
        safe = checkpoint_id.replace("/", "_").replace("..", "_")
        return self.root / f"{safe}.json"

    async def save(self, checkpoint_id: str, payload: Dict[str, Any]) -> AgentCheckpoint:
        path = self._path(checkpoint_id)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._save_sync, checkpoint_id, payload, path)

    def _save_sync(self, checkpoint_id: str, payload: Dict[str, Any], path: Path) -> AgentCheckpoint:
        """同步：跨进程锁内读-改-写 checkpoint（消除并发合并字段丢更新）。"""
        with FileLock(path):
            existing = None
            if path.exists():
                try:
                    existing = AgentCheckpoint.from_dict(json.loads(path.read_text(encoding="utf-8")))
                except Exception:
                    logger.exception("load checkpoint failed: %s", checkpoint_id)
                    existing = None
            base = existing.to_dict() if existing else {"checkpoint_id": checkpoint_id}
            base.update(payload)
            base["checkpoint_id"] = checkpoint_id
            base["updated_at"] = datetime.now().isoformat()
            cp = AgentCheckpoint.from_dict(base)
            atomic_write_text(path, json.dumps(cp.to_dict(), ensure_ascii=False, indent=2))
            return cp

    async def load(self, checkpoint_id: str) -> Optional[AgentCheckpoint]:
        path = self._path(checkpoint_id)
        if not path.exists():
            return None
        try:
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                data = json.loads(await f.read())
            return AgentCheckpoint.from_dict(data)
        except Exception:
            logger.exception("load checkpoint failed: %s", checkpoint_id)
            return None

    async def delete(self, checkpoint_id: str) -> bool:
        path = self._path(checkpoint_id)
        if path.exists():
            path.unlink()
            return True
        return False
