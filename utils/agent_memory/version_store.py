"""
MemoryVersionStore — 记忆 markdown 目标的版本链写入层。

设计（照 `utils/drama_version_store.py` 的 Event Sourcing + OCC + Copy-on-Write 模式，改为同步版）：
  1. Agent 只产出「意图」，本层作为确定性写入器串行落盘，避免并发写同一文件互相覆盖。
  2. 乐观并发（OCC）：调用方携带 expected_version（读到的 head 版本号），写入时 CAS，
     不一致则返回 conflict + conflict_diff，绝不静默覆盖（lost update）。
  3. Copy-on-Write：每次写前把「改前/改后」落成不可变 blob，形成版本链，可 diff / 可回滚。

目标（markdown）：
  rules  -> RULES.md    作品规则
  memory -> MEMORY.md   作品常驻笔记
  user   -> USER.md     用户常驻画像
  org    -> ORG.md      组织共享记忆

版本存储（相对 base_dir，即某作品/用户/org 的 memory 目录）：
  versions/index.json                    版本链索引
  versions/blobs/{vid}.before.md / .after.md  改前/改后快照
"""

from __future__ import annotations

import difflib
import hashlib
import json
import logging
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

TARGET_FILES = {
    "rules": "RULES.md",
    "memory": "MEMORY.md",
    "user": "USER.md",
    "org": "ORG.md",
}

TARGET_LABELS = {
    "rules": "规则",
    "memory": "作品记忆",
    "user": "用户画像",
    "org": "组织记忆",
}


def _short_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]


def unified_diff(before: str, after: str) -> str:
    """返回 unified diff（空串表示无差异）。"""
    if before == after:
        return ""
    return "\n".join(
        difflib.unified_diff(
            (before or "").splitlines(),
            (after or "").splitlines(),
            fromfile="before",
            tofile="after",
            lineterm="",
        )
    )


class MemoryVersionStore:
    """记忆 markdown 版本化写入器（同步，进程内单例按 scope 建）。"""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # 路径
    # ------------------------------------------------------------------
    def _versions_dir(self) -> Path:
        p = self.base_dir / "versions"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _index_path(self) -> Path:
        return self._versions_dir() / "index.json"

    def _blob_path(self, version_id: str, suffix: str) -> Path:
        return self._versions_dir() / "blobs" / f"{version_id}.{suffix}.md"

    def _target_path(self, target: str) -> Path:
        if target not in TARGET_FILES:
            raise ValueError(f"未知目标: {target}（可选 {sorted(TARGET_FILES)}）")
        return self.base_dir / TARGET_FILES[target]

    # ------------------------------------------------------------------
    # 索引
    # ------------------------------------------------------------------
    def _load_index(self) -> List[Dict[str, Any]]:
        path = self._index_path()
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get("versions") or []
        except Exception as e:
            logger.warning("读取记忆版本索引失败: %s (%s)", path, e)
            return []

    def _save_index(self, versions: List[Dict[str, Any]]) -> None:
        path = self._index_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"versions": versions}, ensure_ascii=False, indent=2), encoding="utf-8")

    def head_version(self, target: str) -> Optional[str]:
        for v in reversed(self._load_index()):
            if v.get("target") == target:
                return v.get("version_id")
        return None

    # ------------------------------------------------------------------
    # 读
    # ------------------------------------------------------------------
    def read_target(self, target: str) -> str:
        path = self._target_path(target)
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    # ------------------------------------------------------------------
    # 写（核心）
    # ------------------------------------------------------------------
    def commit(
        self,
        target: str,
        content: str,
        *,
        agent_id: str = "",
        session_id: str = "",
        expected_version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """版本化写入目标 markdown。expected_version 提供时做 CAS。"""
        content = content or ""
        path = self._target_path(target)

        with self._lock:
            before = self.read_target(target)
            before_hash = _short_hash(before)
            after_hash = _short_hash(content)
            head_version_id = self.head_version(target)

            # OCC CAS
            if expected_version and head_version_id != expected_version:
                return {
                    "success": False,
                    "changed": False,
                    "conflict": True,
                    "version_id": None,
                    "target": target,
                    "before_hash": before_hash,
                    "after_hash": after_hash,
                    "diff": "",
                    "conflict_diff": unified_diff(before, content),
                    "content": before,
                    "current_version_id": head_version_id,
                    "message": f"写入冲突：目标已被他人更新（当前版本 {head_version_id}，期望 {expected_version}）",
                }

            # 内容未变 → 幂等 no-op
            if before == content:
                return {
                    "success": True,
                    "changed": False,
                    "conflict": False,
                    "version_id": head_version_id,
                    "target": target,
                    "before_hash": before_hash,
                    "after_hash": after_hash,
                    "diff": "",
                    "content": content,
                }

            version_id = f"v{uuid.uuid4().hex[:10]}"
            now = datetime.now().isoformat()
            entry = {
                "version_id": version_id,
                "target": target,
                "parent_version_id": head_version_id,
                "before_hash": before_hash,
                "after_hash": after_hash,
                "agent_id": agent_id,
                "session_id": session_id,
                "char_count": len(content),
                "created_at": now,
            }

            # 1) Copy-on-Write 快照
            self._write_blob(version_id, "before", before)
            self._write_blob(version_id, "after", content)

            # 2) 写目标文件
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

            # 3) 追加版本链
            versions = self._load_index()
            versions.append(entry)
            self._save_index(versions)

            return {
                "success": True,
                "changed": True,
                "conflict": False,
                "version_id": version_id,
                "parent_version_id": head_version_id,
                "target": target,
                "before_hash": before_hash,
                "after_hash": after_hash,
                "diff": unified_diff(before, content),
                "content": content,
                "created_at": now,
            }

    def _write_blob(self, version_id: str, suffix: str, text: str) -> None:
        path = self._blob_path(version_id, suffix)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text or "", encoding="utf-8")

    def _read_blob(self, version_id: str, suffix: str) -> str:
        path = self._blob_path(version_id, suffix)
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------
    def list_versions(self, target: Optional[str] = None) -> List[Dict[str, Any]]:
        versions = self._load_index()
        if target:
            versions = [v for v in versions if v.get("target") == target]
        return list(reversed(versions))  # 新的在前

    def get_version(self, version_id: str) -> Optional[Dict[str, Any]]:
        for v in self._load_index():
            if v.get("version_id") == version_id:
                before = self._read_blob(version_id, "before")
                after = self._read_blob(version_id, "after")
                return {
                    **v,
                    "before": before,
                    "after": after,
                    "diff": unified_diff(before, after),
                    "target_label": TARGET_LABELS.get(v.get("target"), v.get("target", "")),
                }
        return None

    def diff(self, version_id: str) -> str:
        v = self.get_version(version_id)
        return v.get("diff", "") if v else ""

    def rollback(
        self,
        version_id: str,
        *,
        agent_id: str = "",
        session_id: str = "",
    ) -> Dict[str, Any]:
        v = self.get_version(version_id)
        if not v:
            raise ValueError(f"版本不存在: {version_id}")
        target = v.get("target") or ""
        content = v.get("after") or ""
        return self.commit(
            target,
            content,
            agent_id=agent_id,
            session_id=session_id or f"rollback:{version_id}",
        )


__all__ = [
    "MemoryVersionStore",
    "unified_diff",
    "TARGET_FILES",
    "TARGET_LABELS",
]
