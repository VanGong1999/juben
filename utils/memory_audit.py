"""
记忆审计与快照管理
"""
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from utils.memory_manager import get_unified_memory_manager
from utils.storage_manager import get_storage
from utils.enhanced_context_manager import get_enhanced_context_manager


class MemoryAuditManager:
    def __init__(self, path: str = "data/memory_snapshots.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._cache: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            self._cache = []
            return
        try:
            self._cache = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            self._cache = []

    def _save(self) -> None:
        self.path.write_text(json.dumps(self._cache, ensure_ascii=False, indent=2), encoding="utf-8")

    async def create_snapshot(
        self,
        user_id: str,
        session_id: str,
        project_id: Optional[str] = None,
        label: Optional[str] = None
    ) -> Dict[str, Any]:
        storage = get_storage()
        if not storage._initialized:
            await storage.initialize()

        short_term = await storage.get_chat_messages(user_id, session_id, limit=30)
        memory_manager = get_unified_memory_manager()
        middle_term = await memory_manager.get_middle_term_context(user_id, session_id, "", limit=20)

        context_manager = get_enhanced_context_manager()
        script_summary = await context_manager.get_script_context_summary(user_id, session_id)
        graph_summary = await context_manager.get_graph_context_summary(user_id, session_id)

        snapshot = {
            "id": f"snapshot_{int(datetime.now().timestamp())}",
            "user_id": user_id,
            "session_id": session_id,
            "project_id": project_id,
            "label": label or "自动快照",
            "created_at": datetime.now().isoformat(),
            "short_term_messages": short_term,
            "middle_term_memories": middle_term.get("memories", []),
            "script_summary": script_summary,
            "graph_summary": graph_summary
        }
        # 整合归一：作品维度记忆快照委托给 AgentMemoryService 导出（Phase 5）。
        if project_id:
            try:
                from utils.agent_memory import get_agent_memory_service

                snapshot["agent_memory_export"] = get_agent_memory_service().export_memory(project_id)
            except Exception:
                snapshot["agent_memory_export"] = None
        self._cache.insert(0, snapshot)
        self._save()
        return snapshot

    def list_snapshots(
        self,
        user_id: str,
        session_id: str,
        project_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        results = [
            s for s in self._cache
            if s.get("user_id") == user_id and s.get("session_id") == session_id
        ]
        if project_id:
            results = [s for s in results if s.get("project_id") == project_id]
        return results

    async def restore_snapshot(
        self,
        snapshot_id: str,
        user_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        snapshot = next((s for s in self._cache if s.get("id") == snapshot_id), None)
        if not snapshot:
            raise ValueError("快照不存在")

        if snapshot.get("user_id") != user_id or snapshot.get("session_id") != session_id:
            raise ValueError("快照与当前会话不匹配")

        memory_manager = get_unified_memory_manager()
        await memory_manager.overwrite_middle_term_memories(
            user_id, session_id, snapshot.get("middle_term_memories", [])
        )
        return snapshot

    def create_drama_snapshot(self, drama_id: str) -> Dict[str, Any]:
        """作品记忆快照：委托 AgentMemoryService 全量导出（Phase 5）。"""
        from utils.agent_memory import get_agent_memory_service

        return get_agent_memory_service().export_memory(drama_id)

    def list_drama_versions(self, drama_id: str, target: Optional[str] = None) -> List[Dict[str, Any]]:
        from utils.agent_memory import get_agent_memory_service

        return get_agent_memory_service().list_memory_versions(drama_id, target=target)

    def restore_drama_version(self, drama_id: str, version_id: str) -> Dict[str, Any]:
        """作品记忆回滚：委托 Phase 2 版本链 rollback。"""
        from utils.agent_memory import get_agent_memory_service

        return get_agent_memory_service().rollback_memory_version(drama_id, version_id)

    async def evaluate_quality(
        self,
        user_id: str,
        session_id: str,
        query: str
    ) -> Dict[str, Any]:
        memory_manager = get_unified_memory_manager()
        middle_term = await memory_manager.get_middle_term_context(user_id, session_id, query, limit=20)
        memories = middle_term.get("memories", [])

        tokens = self._tokenize(query)
        hit_count = 0
        for mem in memories:
            text = f"{mem.get('task_summary','')} {mem.get('compressed_summary','')}".lower()
            if any(t in text for t in tokens):
                hit_count += 1

        hit_rate = round(hit_count / len(memories), 4) if memories else 0.0

        conflicts, total_keys = self._detect_conflicts(memories)
        conflict_rate = round(conflicts / total_keys, 4) if total_keys else 0.0

        return {
            "hit_rate": hit_rate,
            "conflict_rate": conflict_rate,
            "memory_count": len(memories),
            "conflict_keys": list(self._conflict_keys(memories))
        }

    def _tokenize(self, text: str) -> List[str]:
        if not text:
            return []
        parts = re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z0-9_]+", text.lower())
        return [p for p in parts if len(p) >= 2]

    def _extract_key_values(self, text: str) -> Dict[str, str]:
        kv: Dict[str, str] = {}
        if not text:
            return kv
        for line in text.splitlines():
            line = line.strip().lstrip("-").strip()
            if ":" in line:
                key, value = line.split(":", 1)
            elif "：" in line:
                key, value = line.split("：", 1)
            elif "=" in line:
                key, value = line.split("=", 1)
            else:
                continue
            key = key.strip()
            value = value.strip()
            if len(key) >= 2 and value:
                kv[key] = value
        return kv

    def _detect_conflicts(self, memories: List[Dict[str, Any]]) -> Tuple[int, int]:
        key_values: Dict[str, set] = {}
        for mem in memories:
            text = f"{mem.get('task_summary','')}\n{mem.get('compressed_summary','')}"
            kv = self._extract_key_values(text)
            for k, v in kv.items():
                key_values.setdefault(k, set()).add(v)
        total_keys = len(key_values)
        conflicts = sum(1 for v in key_values.values() if len(v) > 1)
        return conflicts, total_keys

    def _conflict_keys(self, memories: List[Dict[str, Any]]) -> List[str]:
        key_values: Dict[str, set] = {}
        for mem in memories:
            text = f"{mem.get('task_summary','')}\n{mem.get('compressed_summary','')}"
            kv = self._extract_key_values(text)
            for k, v in kv.items():
                key_values.setdefault(k, set()).add(v)
        return [k for k, v in key_values.items() if len(v) > 1]


_memory_audit_manager: Optional[MemoryAuditManager] = None


def get_memory_audit_manager() -> MemoryAuditManager:
    global _memory_audit_manager
    if _memory_audit_manager is None:
        _memory_audit_manager = MemoryAuditManager()
    return _memory_audit_manager

