"""原子写 + 跨进程文件锁 单测"""

from __future__ import annotations

import json
import threading
from pathlib import Path

from utils.atomic_write import FileLock, atomic_write_text


def test_atomic_write_text_roundtrip(tmp_path: Path):
    p = tmp_path / "a.json"
    atomic_write_text(p, json.dumps({"k": 1}, ensure_ascii=False))
    assert json.loads(p.read_text(encoding="utf-8")) == {"k": 1}
    # 覆盖写
    atomic_write_text(p, json.dumps({"k": 2}, ensure_ascii=False))
    assert json.loads(p.read_text(encoding="utf-8")) == {"k": 2}


def test_atomic_write_creates_parent_dirs(tmp_path: Path):
    p = tmp_path / "nested" / "dir" / "f.json"
    atomic_write_text(p, "x")
    assert p.read_text(encoding="utf-8") == "x"


def test_file_lock_serializes_concurrent_read_modify_write(tmp_path: Path):
    """多线程并发「读-改-写」同一文件，FileLock 应避免丢条目（lost update）。"""
    path = tmp_path / "index.json"
    atomic_write_text(path, json.dumps({"versions": []}))
    errors = []

    def append_one(i: int) -> None:
        try:
            with FileLock(path):
                if path.exists():
                    data = json.loads(path.read_text(encoding="utf-8"))
                else:
                    data = {"versions": []}
                versions = list(data.get("versions") or [])
                versions.append({"id": i})
                atomic_write_text(path, json.dumps({"versions": versions}))
        except Exception as e:  # pragma: no cover
            errors.append(e)

    threads = [threading.Thread(target=append_one, args=(i,)) for i in range(30)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    final = json.loads(path.read_text(encoding="utf-8"))
    assert len(final["versions"]) == 30
