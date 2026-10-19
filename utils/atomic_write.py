"""
原子写工具 — 临时文件 + fsync + os.replace，跨进程安全的文件写入。

多 uvicorn worker / 多进程部署下，`open(path, "w")` 直写会出现：
  1. 读-写-写竞态：后写覆盖先写（lost update）
  2. 崩溃/中断：读到写一半的文件（无一致性保证）

os.replace 是原子 rename：任何时刻读者要么读到完整旧内容、要么读到完整新内容，
不会读到写一半的文件。配合调用方的读-改-写锁/OCC 可进一步消除丢更新。
"""
from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Union

try:
    import fcntl
except ImportError:  # pragma: no cover — Windows 降级为 no-op
    fcntl = None


class FileLock:
    """跨进程排他文件锁（fcntl.flock）。

    用于包围「读-改-写」整段，消除多 worker 下后写覆盖先写（lost update）。
    锁文件为 `<target>.lock`，flock 是 per-open-file-description 的排他锁，
    跨进程/跨线程互斥。不支持 flock 的平台降级为 no-op（进程内仍由 asyncio.Lock 保护）。
    """

    def __init__(self, path: Union[str, Path]) -> None:
        self.lock_path = Path(str(path) + ".lock")
        self._fd = None

    def acquire(self) -> None:
        if fcntl is None:
            return
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._fd = open(self.lock_path, "a+")
        fcntl.flock(self._fd.fileno(), fcntl.LOCK_EX)

    def release(self) -> None:
        if self._fd is None:
            return
        try:
            if fcntl is not None:
                fcntl.flock(self._fd.fileno(), fcntl.LOCK_UN)
        finally:
            self._fd.close()
            self._fd = None

    def __enter__(self) -> "FileLock":
        self.acquire()
        return self

    def __exit__(self, *exc) -> bool:
        self.release()
        return False


def atomic_write_text(path: Union[str, Path], content: str) -> None:
    """同步原子写：写同目录临时文件 → flush + fsync → os.replace。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), prefix=f".{p.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, str(p))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


async def atomic_write_text_async(path: Union[str, Path], content: str) -> None:
    """异步原子写：在 executor 中执行同步原子写，避免阻塞事件循环。"""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, atomic_write_text, str(path), content)
