"""
版本化写回层 — 多 Agent 对话内修改「小传 / 大纲 / 剧本内容」的统一落盘入口。

设计依据（Event Sourcing + OCC + Copy-on-Write，见 docs/调研）：
  1. Agent 只产出「意图」，本层作为确定性写入器串行落盘，天然避免多 Agent 并发写同一文件互相覆盖。
  2. 乐观并发（OCC）：调用方携带 expected_version（读到的 head 版本号），写入时 CAS 校验，
     不一致则返回 conflict + diff，绝不静默覆盖（lost update）。
  3. Copy-on-Write 快照：每次写前把「改前/改后」两份内容落成不可变 blob，形成版本链，
     可 diff / 可回滚 / 可审计。
  4. 进程内锁串行化同进程并发写（单进程 FastAPI 足够）；版本链 + WAL 提供跨进程可审计性。

目标文件（一个短剧 = projects/{drama_id}/）：
  - world      -> bible/world.md            世界观
  - characters -> bible/characters.md       人物小传
  - outline    -> outline/series_outline.md 大纲
  - episode    -> episodes/ep_{n:03d}.md    剧本正文（需 episode_number）

版本存储：
  projects/{drama_id}/versions/index.json         版本链索引
  projects/{drama_id}/versions/blobs/{vid}.before.md / .after.md  改前/改后快照
  data/durable_runs/events/{drama_id}.jsonl        WAL（复用 DurableRunStore）
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiofiles

from utils.atomic_write import atomic_write_text, atomic_write_text_async, FileLock

logger = logging.getLogger(__name__)

# target -> 相对路径（episode 需 episode_number 拼 ep_{n:03d}.md）
TARGET_KINDS = {
    "world": "world",
    "characters": "characters",
    "outline": "outline",
    "episode": "episode",
}

TARGET_LABELS = {
    "world": "世界观",
    "characters": "人物小传",
    "outline": "大纲",
    "episode": "剧本",
}


def _short_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]


def unified_diff(before: str, after: str) -> str:
    """返回 unified diff（空串表示无差异）。"""
    import difflib

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


class DramaVersionStore:
    """版本化写入器（进程内单例）。"""

    def __init__(self, base_dir: str = "projects") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        # 单写锁：串行化「读当前 → 写文件 → 写快照 → 写索引 → 写 WAL」整段，
        # 避免文件与索引的 TOCTOU / 交错。OCC 仍用于语义级冲突检测。
        self._write_lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # 路径
    # ------------------------------------------------------------------
    def _dir(self, drama_id: str) -> Path:
        return self.base_dir / drama_id

    def _versions_dir(self, drama_id: str) -> Path:
        return self._dir(drama_id) / "versions"

    def _index_path(self, drama_id: str) -> Path:
        return self._versions_dir(drama_id) / "index.json"

    def _blob_path(self, drama_id: str, version_id: str, suffix: str) -> Path:
        return self._versions_dir(drama_id) / "blobs" / f"{version_id}.{suffix}.md"

    def resolve_target_path(
        self,
        drama_id: str,
        target: str,
        episode_number: Optional[int] = None,
    ) -> Path:
        """target -> 实际文件路径。"""
        if target == "world":
            return self._dir(drama_id) / "bible" / "world.md"
        if target == "characters":
            return self._dir(drama_id) / "bible" / "characters.md"
        if target == "outline":
            return self._dir(drama_id) / "outline" / "series_outline.md"
        if target == "episode":
            if episode_number is None:
                raise ValueError("episode 目标需要 episode_number")
            return self._dir(drama_id) / "episodes" / f"ep_{int(episode_number):03d}.md"
        raise ValueError(f"未知目标: {target}（可选 {sorted(TARGET_KINDS)}）")

    # ------------------------------------------------------------------
    # 版本索引
    # ------------------------------------------------------------------
    async def _load_index(self, drama_id: str) -> List[Dict[str, Any]]:
        path = self._index_path(drama_id)
        if not path.exists():
            return []
        try:
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                data = json.loads(await f.read())
            return data.get("versions") or []
        except Exception as e:
            logger.warning("读取版本索引失败: %s (%s)", path, e)
            return []

    async def _save_index(self, drama_id: str, versions: List[Dict[str, Any]]) -> None:
        path = self._index_path(drama_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        await atomic_write_text_async(path, json.dumps({"versions": versions}, ensure_ascii=False, indent=2))

    def _append_version_sync(self, index_path: Path, entry: Dict[str, Any]) -> List[Dict[str, Any]]:
        """同步：跨进程锁内读-改-写 index.json（消除并发 append 丢条目）。"""
        with FileLock(index_path):
            versions: List[Dict[str, Any]] = []
            if index_path.exists():
                try:
                    versions = json.loads(index_path.read_text(encoding="utf-8")).get("versions") or []
                except Exception:
                    logger.warning("读取版本索引失败，重建: %s", index_path)
                    versions = []
            versions.append(entry)
            atomic_write_text(index_path, json.dumps({"versions": versions}, ensure_ascii=False, indent=2))
            return versions

    async def _append_version_locked(self, drama_id: str, entry: Dict[str, Any]) -> List[Dict[str, Any]]:
        index_path = self._index_path(drama_id)
        index_path.parent.mkdir(parents=True, exist_ok=True)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._append_version_sync, index_path, entry)

    async def get_head(self, drama_id: str, target: str, episode_number: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """返回该目标最新版本条目（无则 None）。"""
        versions = await self._load_index(drama_id)
        for v in reversed(versions):
            if v.get("target") == target and v.get("episode_number") == episode_number:
                return v
        return None

    # ------------------------------------------------------------------
    # 读（供 read_part 工具 / OCC 携带版本）
    # ------------------------------------------------------------------
    async def read_part(
        self,
        drama_id: str,
        target: str,
        episode_number: Optional[int] = None,
    ) -> Dict[str, Any]:
        path = self.resolve_target_path(drama_id, target, episode_number)
        content = ""
        if path.exists():
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                content = await f.read()
        head = await self.get_head(drama_id, target, episode_number)
        return {
            "target": target,
            "episode_number": episode_number,
            "content": content,
            "version_id": head.get("version_id") if head else None,
            "hash": _short_hash(content),
            "path": str(path),
        }

    # ------------------------------------------------------------------
    # 写（核心）
    # ------------------------------------------------------------------
    async def write(
        self,
        drama_id: str,
        target: str,
        content: str,
        *,
        agent_id: str = "",
        agent_name: str = "",
        session_id: str = "",
        expected_version: Optional[str] = None,
        episode_number: Optional[int] = None,
        title: str = "",
    ) -> Dict[str, Any]:
        """
        版本化写入目标文件。

        expected_version：读到的 head version_id；提供时做 CAS，冲突返回 conflict=True。
        返回：success / changed / conflict / version_id / diff / content 等。
        """
        content = content or ""
        path = self.resolve_target_path(drama_id, target, episode_number)
        path.parent.mkdir(parents=True, exist_ok=True)

        async with self._write_lock:
            before = ""
            if path.exists():
                async with aiofiles.open(path, "r", encoding="utf-8") as f:
                    before = await f.read()
            before_hash = _short_hash(before)
            after_hash = _short_hash(content)

            head = await self.get_head(drama_id, target, episode_number)
            head_version_id = head.get("version_id") if head else None

            # OCC：CAS 校验
            if expected_version and head_version_id != expected_version:
                current = await self.read_part(drama_id, target, episode_number)
                return {
                    "success": False,
                    "changed": False,
                    "conflict": True,
                    "version_id": None,
                    "target": target,
                    "episode_number": episode_number,
                    "before_hash": before_hash,
                    "after_hash": after_hash,
                    "diff": "",
                    "conflict_diff": unified_diff(before, content),
                    "content": current["content"],
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
                    "episode_number": episode_number,
                    "before_hash": before_hash,
                    "after_hash": after_hash,
                    "diff": "",
                    "content": content,
                }

            # 生成新版本
            version_id = f"v{uuid.uuid4().hex[:10]}"
            now = datetime.now().isoformat()
            entry = {
                "version_id": version_id,
                "target": target,
                "episode_number": episode_number,
                "parent_version_id": head_version_id,
                "before_hash": before_hash,
                "after_hash": after_hash,
                "agent_id": agent_id,
                "agent_name": agent_name,
                "session_id": session_id,
                "title": title,
                "word_count": len(content),
                "created_at": now,
            }

            # 1) Copy-on-Write 快照（改前/改后）
            await self._write_blob(drama_id, version_id, "before", before)
            await self._write_blob(drama_id, version_id, "after", content)

            # 2) 写目标文件（原子写，避免写一半被读）
            await atomic_write_text_async(path, content)

            # 3) 追加版本链（跨进程锁内读-改-写，消除并发 append 丢条目）
            await self._append_version_locked(drama_id, entry)

            # 4) 更新 drama.json updated_at
            await self._touch_meta(drama_id)

            # 5) WAL（复用 DurableRunStore）
            await self._append_wal(
                drama_id,
                {
                    "type": "artifact_write",
                    "version_id": version_id,
                    "target": target,
                    "episode_number": episode_number,
                    "parent_version_id": head_version_id,
                    "before_hash": before_hash,
                    "after_hash": after_hash,
                    "agent_id": agent_id,
                    "agent_name": agent_name,
                    "session_id": session_id,
                    "created_at": now,
                },
            )

            return {
                "success": True,
                "changed": True,
                "conflict": False,
                "version_id": version_id,
                "parent_version_id": head_version_id,
                "target": target,
                "episode_number": episode_number,
                "before_hash": before_hash,
                "after_hash": after_hash,
                "diff": unified_diff(before, content),
                "content": content,
                "title": title,
                "created_at": now,
            }

    async def _write_blob(self, drama_id: str, version_id: str, suffix: str, text: str) -> None:
        path = self._blob_path(drama_id, version_id, suffix)
        path.parent.mkdir(parents=True, exist_ok=True)
        await atomic_write_text_async(path, text or "")

    async def _touch_meta(self, drama_id: str) -> None:
        meta_path = self._dir(drama_id) / "drama.json"
        if not meta_path.exists():
            return
        try:
            async with aiofiles.open(meta_path, "r", encoding="utf-8") as f:
                meta = json.loads(await f.read())
            meta["updated_at"] = datetime.now().isoformat()
            await atomic_write_text_async(meta_path, json.dumps(meta, ensure_ascii=False, indent=2))
        except Exception:
            logger.warning("更新 drama.json updated_at 失败: %s", drama_id, exc_info=True)

    async def _append_wal(self, drama_id: str, event: Dict[str, Any]) -> None:
        try:
            from utils.agent_infra.durable import DurableRunStore

            await DurableRunStore().append_event(drama_id, event)
        except Exception:
            logger.debug("版本 WAL 追加跳过", exc_info=True)

    # ------------------------------------------------------------------
    # 版本查询
    # ------------------------------------------------------------------
    async def list_versions(
        self,
        drama_id: str,
        target: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        versions = await self._load_index(drama_id)
        if target:
            versions = [v for v in versions if v.get("target") == target]
        return list(reversed(versions))  # 新的在前

    async def get_version(self, drama_id: str, version_id: str) -> Optional[Dict[str, Any]]:
        versions = await self._load_index(drama_id)
        for v in versions:
            if v.get("version_id") == version_id:
                before = await self._read_blob(drama_id, version_id, "before")
                after = await self._read_blob(drama_id, version_id, "after")
                return {
                    **v,
                    "before": before,
                    "after": after,
                    "diff": unified_diff(before, after),
                    "target_label": TARGET_LABELS.get(v.get("target"), v.get("target", "")),
                }
        return None

    async def rollback(
        self,
        drama_id: str,
        version_id: str,
        *,
        agent_id: str = "",
        agent_name: str = "",
        session_id: str = "",
    ) -> Dict[str, Any]:
        """把目标文件回滚到指定版本的内容（回滚本身也记为一次新版本）。"""
        version = await self.get_version(drama_id, version_id)
        if not version:
            raise ValueError(f"版本不存在: {version_id}")
        target = version.get("target") or ""
        episode_number = version.get("episode_number")
        content = version.get("after") or ""
        return await self.write(
            drama_id,
            target,
            content,
            agent_id=agent_id,
            agent_name=agent_name or f"rollback:{version_id}",
            session_id=session_id,
            episode_number=episode_number,
            title=f"回滚到 {version_id}",
        )

    async def _read_blob(self, drama_id: str, version_id: str, suffix: str) -> str:
        path = self._blob_path(drama_id, version_id, suffix)
        if not path.exists():
            return ""
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            return await f.read()


_store: Optional[DramaVersionStore] = None


def get_drama_version_store() -> DramaVersionStore:
    global _store
    if _store is None:
        _store = DramaVersionStore()
    return _store


__all__ = [
    "DramaVersionStore",
    "get_drama_version_store",
    "unified_diff",
    "TARGET_KINDS",
    "TARGET_LABELS",
]
