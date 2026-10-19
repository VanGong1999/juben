"""
Durable Execution — 持久化 run 状态、崩溃回收、Resume
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles

logger = logging.getLogger(__name__)


class DurableRunStore:
    """通用 durable run（文件落盘）。Atelier 也可调用 reclaim 逻辑。"""

    def __init__(self, root: Optional[str] = None) -> None:
        self.root = Path(root or "data/durable_runs")
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _safe_run_id(run_id: str) -> str:
        safe = str(run_id).replace("/", "_").replace("\\", "_")
        while ".." in safe:
            safe = safe.replace("..", "_")
        safe = safe.strip(".")
        return safe or "_"

    def _path(self, run_id: str) -> Path:
        return self.root / f"{self._safe_run_id(run_id)}.json"

    async def save(self, run: Dict[str, Any]) -> Dict[str, Any]:
        run = dict(run)
        run["updated_at"] = datetime.now().isoformat()
        path = self._path(run["run_id"])
        async with aiofiles.open(path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(run, ensure_ascii=False, indent=2, default=str))
        return run

    async def load(self, run_id: str) -> Optional[Dict[str, Any]]:
        path = self._path(run_id)
        if not path.exists():
            return None
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            return json.loads(await f.read())

    async def append_event(self, run_id: str, event: Dict[str, Any]) -> None:
        """Append-only 事件日志，便于 Replay。"""
        log_dir = self.root / "events"
        log_dir.mkdir(parents=True, exist_ok=True)
        path = log_dir / f"{self._safe_run_id(run_id)}.jsonl"
        event = dict(event)
        event.setdefault("ts", datetime.now().isoformat())
        async with aiofiles.open(path, "a", encoding="utf-8") as f:
            await f.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")

    async def load_events(self, run_id: str) -> List[Dict[str, Any]]:
        path = self.root / "events" / f"{self._safe_run_id(run_id)}.jsonl"
        if not path.exists():
            return []
        events: List[Dict[str, Any]] = []
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            async for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        return events


async def reclaim_stale_runs(
    *,
    stale_after_seconds: int = 1800,
    projects_root: str = "projects",
    run_filename: str = "atelier_run.json",
) -> List[Dict[str, Any]]:
    """
    扫描 projects/*/atelier_run.json，把超时仍为 running 的步骤回收为 pending。
    进程重启后调用一次即可恢复可执行状态。
    """
    reclaimed: List[Dict[str, Any]] = []
    base = Path(projects_root)
    if not base.exists():
        return reclaimed

    cutoff = datetime.now() - timedelta(seconds=stale_after_seconds)

    for folder in base.iterdir():
        if not folder.is_dir():
            continue
        path = folder / run_filename
        if not path.exists():
            continue
        try:
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                run = json.loads(await f.read())
        except Exception:
            logger.exception("read run failed: %s", path)
            continue

        changed = False
        updated_at = run.get("updated_at") or run.get("created_at") or ""
        try:
            ts = datetime.fromisoformat(updated_at) if updated_at else None
        except ValueError:
            ts = None

        for step in run.get("steps") or []:
            if step.get("status") != "running":
                continue
            # 无时间戳或已过期 → reclaim
            if ts is None or ts < cutoff:
                step["status"] = "pending"
                step["error"] = (step.get("error") or "") + " [reclaimed after restart/stale]"
                changed = True
                reclaimed.append(
                    {
                        "drama_id": run.get("drama_id"),
                        "run_id": run.get("run_id"),
                        "step_id": step.get("id"),
                    }
                )

        if changed:
            if run.get("status") == "running":
                run["status"] = "ready"
            run["updated_at"] = datetime.now().isoformat()
            async with aiofiles.open(path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(run, ensure_ascii=False, indent=2))

    if reclaimed:
        logger.info("[agent_infra] reclaimed %s stale steps", len(reclaimed))
    return reclaimed
