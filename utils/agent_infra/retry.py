"""
Retry / Timeout / Idempotency
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional, TypeVar

import aiofiles

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    timeout_s: float = 120.0
    backoff: float = 2.0
    initial_delay: float = 1.0
    retry_on: tuple = (Exception,)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_attempts": self.max_attempts,
            "timeout_s": self.timeout_s,
            "backoff": self.backoff,
            "initial_delay": self.initial_delay,
        }


async def with_retry_timeout(
    fn: Callable[[], Awaitable[T]],
    policy: Optional[RetryPolicy] = None,
    *,
    label: str = "op",
) -> T:
    policy = policy or RetryPolicy()
    delay = policy.initial_delay
    last_exc: Optional[BaseException] = None

    for attempt in range(1, policy.max_attempts + 1):
        try:
            return await asyncio.wait_for(fn(), timeout=policy.timeout_s)
        except asyncio.TimeoutError as e:
            last_exc = e
            logger.warning("[%s] timeout attempt=%s/%s", label, attempt, policy.max_attempts)
        except policy.retry_on as e:  # type: ignore[misc]
            last_exc = e
            logger.warning("[%s] retry attempt=%s/%s err=%s", label, attempt, policy.max_attempts, e)
        if attempt < policy.max_attempts:
            await asyncio.sleep(delay)
            delay *= policy.backoff

    assert last_exc is not None
    raise last_exc


class IdempotencyStore:
    """
    幂等键存储：同一 key 在 TTL 内返回首次结果，避免重复副作用。
    落盘到 data/idempotency/。
    """

    def __init__(self, root: Optional[str] = None, ttl_seconds: int = 86400) -> None:
        self.root = Path(root or "data/idempotency")
        self.root.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds

    @staticmethod
    def make_key(*parts: Any) -> str:
        raw = json.dumps(parts, ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

    def _path(self, key: str) -> Path:
        safe = key.replace("/", "_")
        return self.root / f"{safe}.json"

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                data = json.loads(await f.read())
            expires = datetime.fromisoformat(data["expires_at"])
            if datetime.now() > expires:
                path.unlink(missing_ok=True)
                return None
            return data.get("result")
        except Exception:
            logger.exception("idempotency get failed: %s", key)
            return None

    async def put(self, key: str, result: Any) -> None:
        path = self._path(key)
        payload = {
            "key": key,
            "result": result,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(seconds=self.ttl_seconds)).isoformat(),
        }
        async with aiofiles.open(path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(payload, ensure_ascii=False, indent=2, default=str))

    async def run_once(
        self,
        key: str,
        fn: Callable[[], Awaitable[T]],
    ) -> T:
        cached = await self.get(key)
        if cached is not None:
            return cached  # type: ignore[return-value]
        result = await fn()
        await self.put(key, result)
        return result
