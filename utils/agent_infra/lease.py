"""
Job Lease + Heartbeat — 多 Worker 认领任务，崩溃后可回收
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class JobLease:
    lease_id: str
    resource_key: str
    owner: str
    expires_at: datetime
    metadata: Dict[str, Any]

    @property
    def expired(self) -> bool:
        return datetime.now() >= self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lease_id": self.lease_id,
            "resource_key": self.resource_key,
            "owner": self.owner,
            "expires_at": self.expires_at.isoformat(),
            "metadata": self.metadata,
        }


class LeaseManager:
    """
    优先 Redis（复用 distributed_lock 语义）；不可用时内存 fallback。
    """

    def __init__(self, ttl_seconds: int = 60) -> None:
        self.ttl_seconds = ttl_seconds
        self._memory: Dict[str, JobLease] = {}
        self._lock = asyncio.Lock()
        self._redis = None

    async def _get_redis(self):
        if self._redis is not None:
            return self._redis
        try:
            from utils.redis_client import get_redis_client

            self._redis = await get_redis_client()
        except Exception:
            self._redis = False
        return self._redis if self._redis is not False else None

    def _redis_key(self, resource_key: str) -> str:
        return f"agent_infra:lease:{resource_key}"

    async def acquire(
        self,
        resource_key: str,
        *,
        owner: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[JobLease]:
        owner = owner or f"worker_{uuid.uuid4().hex[:8]}"
        lease_id = f"lease_{uuid.uuid4().hex[:12]}"
        expires = datetime.now() + timedelta(seconds=self.ttl_seconds)
        lease = JobLease(
            lease_id=lease_id,
            resource_key=resource_key,
            owner=owner,
            expires_at=expires,
            metadata=dict(metadata or {}),
        )

        redis = await self._get_redis()
        if redis is not None:
            try:
                key = self._redis_key(resource_key)
                ok = await redis.set(
                    key,
                    f"{lease_id}|{owner}|{expires.isoformat()}",
                    nx=True,
                    ex=self.ttl_seconds,
                )
                if not ok:
                    return None
                return lease
            except Exception:
                logger.warning("redis lease acquire failed, fallback memory", exc_info=True)

        async with self._lock:
            existing = self._memory.get(resource_key)
            if existing and not existing.expired:
                return None
            self._memory[resource_key] = lease
            return lease

    async def heartbeat(self, lease: JobLease) -> bool:
        expires = datetime.now() + timedelta(seconds=self.ttl_seconds)
        lease.expires_at = expires
        redis = await self._get_redis()
        if redis is not None:
            try:
                key = self._redis_key(lease.resource_key)
                val = await redis.get(key)
                if not val or not str(val).startswith(lease.lease_id):
                    return False
                await redis.set(
                    key,
                    f"{lease.lease_id}|{lease.owner}|{expires.isoformat()}",
                    ex=self.ttl_seconds,
                )
                return True
            except Exception:
                logger.warning("redis lease heartbeat failed", exc_info=True)

        async with self._lock:
            current = self._memory.get(lease.resource_key)
            if not current or current.lease_id != lease.lease_id:
                return False
            self._memory[lease.resource_key] = lease
            return True

    async def release(self, lease: JobLease) -> None:
        redis = await self._get_redis()
        if redis is not None:
            try:
                key = self._redis_key(lease.resource_key)
                val = await redis.get(key)
                if val and str(val).startswith(lease.lease_id):
                    await redis.delete(key)
            except Exception:
                logger.warning("redis lease release failed", exc_info=True)

        async with self._lock:
            current = self._memory.get(lease.resource_key)
            if current and current.lease_id == lease.lease_id:
                del self._memory[lease.resource_key]
