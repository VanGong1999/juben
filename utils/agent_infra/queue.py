"""
Task Queue & Worker Pool — 优先级队列、并发、背压

进程内实现；生产可换成 Redis Streams / Arq，接口保持不变。
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

JobHandler = Callable[["Job"], Awaitable[Any]]


class JobPriority(IntEnum):
    LOW = 30
    NORMAL = 20
    HIGH = 10
    CRITICAL = 0


@dataclass(order=True)
class _QueueItem:
    priority: int
    seq: int
    job: Any = field(compare=False)


@dataclass
class Job:
    job_id: str
    kind: str
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: JobPriority = JobPriority.NORMAL
    status: str = "queued"  # queued | running | done | failed | cancelled
    attempts: int = 0
    max_attempts: int = 3
    result: Any = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    idempotency_key: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "kind": self.kind,
            "payload": self.payload,
            "priority": int(self.priority),
            "status": self.status,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "idempotency_key": self.idempotency_key,
        }


class QueueFullError(Exception):
    pass


class TaskQueue:
    """有界优先级队列；满时拒绝入队（背压）。"""

    def __init__(self, maxsize: int = 200, max_tracked: int = 1000) -> None:
        self.maxsize = maxsize
        self.max_tracked = max_tracked
        self._pq: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=maxsize)
        self._jobs: Dict[str, Job] = {}
        self._seq = 0
        self._idempotency: Dict[str, str] = {}  # key -> job_id
        self._lock = asyncio.Lock()

    def _gc_jobs(self) -> None:
        """淘汰已终态的旧任务，防止 _jobs/_idempotency 无界增长。"""
        if len(self._jobs) <= self.max_tracked:
            return
        terminal = [j for j in self._jobs.values() if j.status in ("done", "failed", "cancelled")]
        terminal.sort(key=lambda j: j.created_at)
        overflow = len(self._jobs) - self.max_tracked
        for j in terminal[:overflow]:
            self._jobs.pop(j.job_id, None)
            if j.idempotency_key:
                self._idempotency.pop(j.idempotency_key, None)

    @property
    def size(self) -> int:
        return self._pq.qsize()

    def get_job(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    async def enqueue(
        self,
        kind: str,
        payload: Optional[Dict[str, Any]] = None,
        *,
        priority: JobPriority = JobPriority.NORMAL,
        max_attempts: int = 3,
        idempotency_key: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> Job:
        async with self._lock:
            if idempotency_key and idempotency_key in self._idempotency:
                existing_id = self._idempotency[idempotency_key]
                existing = self._jobs.get(existing_id)
                if existing and existing.status in ("queued", "running", "done"):
                    return existing

            if self._pq.full():
                raise QueueFullError(f"queue full (maxsize={self.maxsize})")

            jid = job_id or f"job_{uuid.uuid4().hex[:12]}"
            job = Job(
                job_id=jid,
                kind=kind,
                payload=dict(payload or {}),
                priority=priority,
                max_attempts=max_attempts,
                idempotency_key=idempotency_key,
            )
            self._jobs[jid] = job
            if idempotency_key:
                self._idempotency[idempotency_key] = jid
            self._gc_jobs()
            self._seq += 1
            await self._pq.put(_QueueItem(priority=int(priority), seq=self._seq, job=job))
            return job

    async def dequeue(self, timeout: Optional[float] = None) -> Optional[Job]:
        try:
            if timeout is None:
                item = await self._pq.get()
            else:
                item = await asyncio.wait_for(self._pq.get(), timeout=timeout)
            return item.job
        except asyncio.TimeoutError:
            return None

    def list_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        jobs = sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)
        return [j.to_dict() for j in jobs[:limit]]

    def stats(self) -> Dict[str, Any]:
        by_status: Dict[str, int] = {}
        for j in self._jobs.values():
            by_status[j.status] = by_status.get(j.status, 0) + 1
        return {
            "queued": self.size,
            "maxsize": self.maxsize,
            "by_status": by_status,
            "total_tracked": len(self._jobs),
        }


class WorkerPool:
    """并发 Worker：从队列取 Job，调用注册的 handler。"""

    def __init__(
        self,
        queue: TaskQueue,
        *,
        concurrency: int = 4,
        handlers: Optional[Dict[str, JobHandler]] = None,
    ) -> None:
        self.queue = queue
        self.concurrency = concurrency
        self.handlers: Dict[str, JobHandler] = dict(handlers or {})
        self._workers: List[asyncio.Task] = []
        self._running = False
        self._default_handler: Optional[JobHandler] = None

    def register(self, kind: str, handler: JobHandler) -> None:
        self.handlers[kind] = handler

    def set_default(self, handler: JobHandler) -> None:
        self._default_handler = handler

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._workers = [
            asyncio.create_task(self._worker_loop(i), name=f"agent-worker-{i}")
            for i in range(self.concurrency)
        ]
        logger.info("[agent_infra] WorkerPool started concurrency=%s", self.concurrency)

    async def stop(self) -> None:
        self._running = False
        for t in self._workers:
            t.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        logger.info("[agent_infra] WorkerPool stopped")

    async def _worker_loop(self, worker_id: int) -> None:
        while self._running:
            job = await self.queue.dequeue(timeout=1.0)
            if not job:
                continue
            await self._run_job(job, worker_id)

    async def _run_job(self, job: Job, worker_id: int) -> None:
        handler = self.handlers.get(job.kind) or self._default_handler
        if not handler:
            job.status = "failed"
            job.error = f"no handler for kind={job.kind}"
            job.finished_at = datetime.now().isoformat()
            return

        job.status = "running"
        job.started_at = datetime.now().isoformat()
        job.attempts += 1
        try:
            result = await handler(job)
            job.result = result
            job.status = "done"
        except Exception as e:
            logger.exception("[agent_infra] job failed worker=%s job=%s", worker_id, job.job_id)
            job.error = str(e)
            if job.attempts < job.max_attempts:
                job.status = "queued"
                # 重新入队（降级优先级避免饿死）
                try:
                    await self.queue._pq.put(
                        _QueueItem(
                            priority=min(int(job.priority) + 5, 99),
                            seq=self.queue._seq + 1,
                            job=job,
                        )
                    )
                    self.queue._seq += 1
                except asyncio.QueueFull:
                    job.status = "failed"
                    job.error = f"{job.error}; requeue failed (backpressure)"
            else:
                job.status = "failed"
        finally:
            if job.status in ("done", "failed"):
                job.finished_at = datetime.now().isoformat()


_global_queue: Optional[TaskQueue] = None
_global_pool: Optional[WorkerPool] = None


def get_task_queue(maxsize: int = 200) -> TaskQueue:
    global _global_queue
    if _global_queue is None:
        _global_queue = TaskQueue(maxsize=maxsize)
    return _global_queue


async def get_worker_pool(concurrency: int = 4) -> WorkerPool:
    global _global_pool
    q = get_task_queue()
    if _global_pool is None:
        _global_pool = WorkerPool(q, concurrency=concurrency)
        await _global_pool.start()
    return _global_pool
