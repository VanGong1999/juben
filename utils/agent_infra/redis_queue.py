"""
Redis Streams 任务队列 — 多进程 Worker 可认领

键：agent_infra:jobs (stream)
消费组：agent_workers
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, List, Optional

from .lease import LeaseManager
from .queue import Job, JobPriority

logger = logging.getLogger(__name__)

STREAM_KEY = "agent_infra:jobs"
GROUP = "agent_workers"
JobHandler = Callable[[Job], Awaitable[Any]]


class RedisTaskQueue:
    def __init__(self, stream_key: str = STREAM_KEY, group: str = GROUP) -> None:
        self.stream_key = stream_key
        self.group = group
        self._redis = None
        self._jobs: Dict[str, Job] = {}
        self.lease_manager = LeaseManager(ttl_seconds=90)

    async def _client(self):
        if self._redis is not None:
            return self._redis
        try:
            from utils.redis_client import get_redis_client

            self._redis = await get_redis_client()
            if self._redis:
                try:
                    await self._redis.xgroup_create(self.stream_key, self.group, id="0", mkstream=True)
                except Exception as e:
                    # BUSYGROUP 已存在
                    if "BUSYGROUP" not in str(e).upper():
                        logger.debug("xgroup_create: %s", e)
        except Exception:
            logger.warning("RedisTaskQueue: redis unavailable", exc_info=True)
            self._redis = False
        return self._redis if self._redis is not False else None

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
        redis = await self._client()
        if redis is None:
            raise RuntimeError("Redis unavailable for RedisTaskQueue")

        if idempotency_key:
            idk = f"agent_infra:idem:{idempotency_key}"
            existing = await redis.get(idk)
            if existing:
                cached = self._jobs.get(existing) or Job(
                    job_id=existing, kind=kind, payload=dict(payload or {}), status="queued"
                )
                return cached
            # 原子占位（SET NX）：并发下仅一人入队，避免重复副作用
            acquired = await redis.set(idk, jid, ex=86400, nx=True)
            if not acquired:
                existing = await redis.get(idk)
                if existing:
                    cached = self._jobs.get(existing) or Job(
                        job_id=existing, kind=kind, payload=dict(payload or {}), status="queued"
                    )
                    return cached

        fields = {
            "job_id": jid,
            "kind": kind,
            "payload": json.dumps(job.payload, ensure_ascii=False),
            "priority": str(int(priority)),
            "max_attempts": str(max_attempts),
            "created_at": job.created_at,
        }
        try:
            await redis.xadd(self.stream_key, fields, maxlen=5000, approximate=True)
        except Exception:
            # xadd 失败：回滚幂等键，否则任务永久丢失（幂等键占用但从未入队）
            if idempotency_key:
                try:
                    await redis.delete(f"agent_infra:idem:{idempotency_key}")
                except Exception:
                    logger.exception("rollback idempotency key failed")
            raise
        return job

    async def claim(
        self,
        consumer: str,
        *,
        count: int = 1,
        block_ms: int = 2000,
    ) -> List[Job]:
        redis = await self._client()
        if redis is None:
            return []
        try:
            results = await redis.xreadgroup(
                self.group,
                consumer,
                streams={self.stream_key: ">"},
                count=count,
                block=block_ms,
            )
        except Exception:
            logger.exception("xreadgroup failed")
            return []

        jobs: List[Job] = []
        if not results:
            return jobs
        for _stream, messages in results:
            for msg_id, fields in messages:
                # redis-py may return bytes
                def _s(v: Any) -> str:
                    return v.decode() if isinstance(v, bytes) else str(v)

                fields = {_s(k): _s(v) for k, v in fields.items()}
                job = Job(
                    job_id=fields.get("job_id") or str(msg_id),
                    kind=fields.get("kind") or "unknown",
                    payload=json.loads(fields.get("payload") or "{}"),
                    priority=JobPriority(int(fields.get("priority") or 20)),
                    max_attempts=int(fields.get("max_attempts") or 3),
                    status="running",
                    started_at=datetime.now().isoformat(),
                )
                job.payload["_redis_msg_id"] = _s(msg_id)
                lease = await self.lease_manager.acquire(
                    f"job:{job.job_id}",
                    owner=consumer,
                    metadata={"msg_id": _s(msg_id)},
                )
                if not lease:
                    # 未能拿到 lease，放回（不 ACK）
                    continue
                job.payload["_lease_id"] = lease.lease_id
                self._jobs[job.job_id] = job
                jobs.append(job)
        return jobs

    async def ack(self, job: Job) -> None:
        redis = await self._client()
        msg_id = (job.payload or {}).get("_redis_msg_id")
        if redis and msg_id:
            try:
                await redis.xack(self.stream_key, self.group, msg_id)
            except Exception:
                logger.exception("xack failed")
        lease_id = (job.payload or {}).get("_lease_id")
        if lease_id:
            from .lease import JobLease

            # best-effort release by re-acquiring pattern — use release with stub
            lease = JobLease(
                lease_id=lease_id,
                resource_key=f"job:{job.job_id}",
                owner="ack",
                expires_at=datetime.now(),
                metadata={},
            )
            await self.lease_manager.release(lease)

    def get_job(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    async def stats(self) -> Dict[str, Any]:
        redis = await self._client()
        if redis is None:
            return {"backend": "redis", "available": False}
        try:
            length = await redis.xlen(self.stream_key)
            return {"backend": "redis", "available": True, "stream_length": length, "group": self.group}
        except Exception as e:
            return {"backend": "redis", "available": False, "error": str(e)}


class RedisWorkerPool:
    def __init__(
        self,
        queue: RedisTaskQueue,
        *,
        concurrency: int = 2,
        consumer_prefix: str = "worker",
        handlers: Optional[Dict[str, JobHandler]] = None,
    ) -> None:
        self.queue = queue
        self.concurrency = concurrency
        self.consumer_prefix = consumer_prefix
        self.handlers: Dict[str, JobHandler] = dict(handlers or {})
        self._tasks: List[asyncio.Task] = []
        self._running = False
        self._default: Optional[JobHandler] = None

    def register(self, kind: str, handler: JobHandler) -> None:
        self.handlers[kind] = handler

    def set_default(self, handler: JobHandler) -> None:
        self._default = handler

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._tasks = [
            asyncio.create_task(self._loop(f"{self.consumer_prefix}-{i}"), name=f"redis-worker-{i}")
            for i in range(self.concurrency)
        ]
        logger.info("[agent_infra] RedisWorkerPool started n=%s", self.concurrency)

    async def stop(self) -> None:
        self._running = False
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def _loop(self, consumer: str) -> None:
        while self._running:
            try:
                jobs = await self.queue.claim(consumer, count=1, block_ms=2000)
                for job in jobs:
                    await self._run(job)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("redis worker loop error")
                await asyncio.sleep(1)

    async def _run(self, job: Job) -> None:
        handler = self.handlers.get(job.kind) or self._default
        job.attempts += 1
        try:
            if not handler:
                raise RuntimeError(f"no handler for {job.kind}")
            job.result = await handler(job)
            job.status = "done"
        except Exception as e:
            job.error = str(e)
            job.status = "failed" if job.attempts >= job.max_attempts else "queued"
            logger.exception("redis job failed: %s", job.job_id)
        finally:
            job.finished_at = datetime.now().isoformat()
            if job.status in ("done", "failed"):
                await self.queue.ack(job)


_redis_queue: Optional[RedisTaskQueue] = None
_redis_pool: Optional[RedisWorkerPool] = None


async def get_redis_task_queue() -> RedisTaskQueue:
    global _redis_queue
    if _redis_queue is None:
        _redis_queue = RedisTaskQueue()
    return _redis_queue


async def get_redis_worker_pool(concurrency: int = 2) -> RedisWorkerPool:
    global _redis_pool
    q = await get_redis_task_queue()
    if _redis_pool is None:
        _redis_pool = RedisWorkerPool(q, concurrency=concurrency)
        await _register_builtin_handlers(_redis_pool)
        await _redis_pool.start()
    return _redis_pool


async def _register_builtin_handlers(pool: RedisWorkerPool) -> None:
    async def echo(job: Job):
        return {"echo": job.payload, "kind": job.kind}

    async def atelier_step(job: Job):
        """后台执行 atelier 单步（非流式收集全文）。"""
        from utils.atelier_pipeline import execute_step

        run_id = job.payload["run_id"]
        step_id = job.payload["step_id"]
        chunks: List[str] = []
        final = None
        async for ev in execute_step(
            run_id,
            step_id,
            drama_id=job.payload.get("drama_id"),
            user_id=job.payload.get("user_id"),
        ):
            if ev.get("event_type") == "llm_chunk" and isinstance(ev.get("data"), str):
                chunks.append(ev["data"])
            if ev.get("event_type") == "complete":
                final = ev.get("data")
        return {"chunks": len(chunks), "complete": final}

    async def tool_loop_job(job: Job):
        from utils.agent_infra.runtime import run_tool_loop
        from utils.agent_tools import ToolContext, get_agent_tool_registry, get_tool_harness
        from utils.llm_client import get_llm_client

        from utils.agent_infra.disclosure import prepare_disclosure

        client = get_llm_client(provider=job.payload.get("provider") or "zhipu")
        registry = get_agent_tool_registry()
        names = job.payload.get("tool_names")
        allow_write = bool(job.payload.get("allow_write"))
        disclosure = prepare_disclosure(
            registry,
            extra_core=list(names) if names else None,
            include_meta=True,
            allow_write=allow_write,
        )
        messages = list(job.payload.get("messages") or [])
        if disclosure.prompt_append:
            if messages and messages[0].get("role") == "system":
                messages[0] = {
                    **messages[0],
                    "content": (messages[0].get("content") or "") + "\n\n" + disclosure.prompt_append,
                }
            else:
                messages.insert(0, {"role": "system", "content": disclosure.prompt_append})
        result = await run_tool_loop(
            client=client,
            messages=messages,
            tools=disclosure.tools,
            harness=get_tool_harness(),
            tool_ctx=ToolContext(
                user_id=job.payload.get("user_id") or "default_user",
                drama_id=job.payload.get("drama_id"),
                allow_write=allow_write,
                metadata={"activated_tools": sorted(disclosure.activated)},
            ),
            max_steps=int(job.payload.get("max_steps") or 8),
            checkpoint_id=job.payload.get("checkpoint_id"),
        )
        return result.to_dict()

    pool.register("echo", echo)
    pool.register("atelier_step", atelier_step)
    pool.register("tool_loop", tool_loop_job)
    pool.set_default(echo)
