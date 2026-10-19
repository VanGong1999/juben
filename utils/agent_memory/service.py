"""
AgentMemoryService — 生产级五层记忆门面

对齐:
- WquGuru: 规则 / 常驻 / 历史召回 / 证据治理 / 技能沉淀
- 5-Layer Playbook: Working / Episodic / Semantic / Procedural / Forgetting
- 业务: 竖屏短剧连载（作品隔离 + Bible + Skills）
"""

from __future__ import annotations

import json
import logging
import math
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .governance import audit_entry, evidence_ref, require_clean
from .ontology import (
    STRENGTH_FLOOR,
    default_scope_for,
    expires_days_for,
    ontology_schema,
    strength_s_for,
    validate_fact,
)
from .store import MemoryStore
from .types import (
    SCHEMA_VERSION,
    Confidence,
    Episode,
    EpisodeOutcome,
    FactStatus,
    Reflection,
    SemanticFact,
    SkillRecord,
    WorkingMemoryBundle,
    new_id,
)
from .vector_index import MemoryVectorIndex
from .version_store import MemoryVersionStore, unified_diff

logger = logging.getLogger(__name__)


class AgentMemoryService:
    def __init__(self, store: Optional[MemoryStore] = None):
        self.store = store or MemoryStore()
        self._version_stores: Dict[str, MemoryVersionStore] = {}

    # ---------- version stores ----------
    def _vs(self, base_dir: Path) -> MemoryVersionStore:
        key = str(base_dir)
        vs = self._version_stores.get(key)
        if vs is None:
            vs = MemoryVersionStore(base_dir)
            self._version_stores[key] = vs
        return vs

    def _drama_vs(self, drama_id: str) -> MemoryVersionStore:
        return self._vs(self.store.drama_memory_dir(drama_id))

    def _user_vs(self, user_id: str) -> MemoryVersionStore:
        return self._vs(self.store.user_memory_dir(user_id))

    def _org_vs(self) -> MemoryVersionStore:
        return self._vs(self.store.org_memory_dir())

    # ---------- semantic OCC head ----------
    def _semantic_head(self, drama_id: str) -> int:
        return int(self.store.read_meta(drama_id).get("head_version") or 0)

    def _bump_semantic_head(self, drama_id: str) -> int:
        meta = self.store.read_meta(drama_id)
        head = int(meta.get("head_version") or 0) + 1
        meta["head_version"] = head
        meta["updated_at"] = datetime.now().isoformat()
        self.store.write_meta(drama_id, meta)
        return head

    @staticmethod
    def _conflict(expected_version: Optional[str], current: Any) -> Dict[str, Any]:
        return {
            "conflict": True,
            "current_version": current,
            "expected_version": expected_version,
            "message": f"并发冲突：当前版本 {current}，期望 {expected_version}，请重读后重试",
        }

    # ==================== Scaffold ====================

    def ensure(self, *, user_id: Optional[str] = None, drama_id: Optional[str] = None) -> Dict[str, str]:
        paths = {}
        if drama_id:
            d = self.store.ensure_drama_scaffold(drama_id)
            paths["drama_memory"] = str(d)
        if user_id:
            u = self.store.ensure_user_scaffold(user_id)
            paths["user_memory"] = str(u)
        return paths

    # ==================== L1 Rules ====================

    def get_rules(self, drama_id: str) -> str:
        self.store.ensure_drama_scaffold(drama_id)
        return self.store.read_text(self.store.drama_memory_dir(drama_id) / "RULES.md")

    def set_rules(
        self,
        drama_id: str,
        content: str,
        *,
        user_id: Optional[str] = None,
        actor: Optional[str] = None,
        session_id: Optional[str] = None,
        expected_version: Optional[str] = None,
    ) -> Dict[str, Any]:
        self.store.ensure_drama_scaffold(drama_id)
        require_clean(content)
        with self.store.lock_for(drama_id):
            result = self._drama_vs(drama_id).commit(
                "rules",
                content,
                agent_id=actor or "",
                session_id=session_id or "",
                expected_version=expected_version,
            )
            self.append_audit(
                action="update",
                layer="rules",
                target_id="RULES.md",
                user_id=user_id,
                drama_id=drama_id,
                agent_id=actor,
                before=content,
                after=content,
                detail={
                    "version_id": result.get("version_id"),
                    "before_hash": result.get("before_hash"),
                    "after_hash": result.get("after_hash"),
                    "conflict": result.get("conflict"),
                },
            )
            return result

    # ==================== L2 Resident ====================

    def get_user_resident(self, user_id: str) -> str:
        self.store.ensure_user_scaffold(user_id)
        return self.store.read_text(self.store.user_memory_dir(user_id) / "USER.md")

    def set_user_resident(
        self,
        user_id: str,
        content: str,
        *,
        skip_injection_scan: bool = False,
        actor: Optional[str] = None,
        session_id: Optional[str] = None,
        expected_version: Optional[str] = None,
    ) -> Dict[str, Any]:
        self.store.ensure_user_scaffold(user_id)
        if not skip_injection_scan:
            require_clean(content)
        # 常驻硬限制：逼合并，避免 token 税失控（Hermes 风格）
        if len(content) > 4000:
            raise ValueError("USER.md 超过 4000 字符，请压缩后再写（只保留身份/偏好/不变量）")
        with self.store.lock_for(f"user:{user_id}"):
            result = self._user_vs(user_id).commit(
                "user",
                content,
                agent_id=actor or "",
                session_id=session_id or "",
                expected_version=expected_version,
            )
            # 用户级审计落到用户目录
            try:
                path = self.store.user_memory_dir(user_id) / "audit.jsonl"
                self.store.append_jsonl(
                    path,
                    audit_entry(
                        action="update",
                        layer="resident",
                        target_id="USER.md",
                        user_id=user_id,
                        agent_id=actor,
                        before=content,
                        after=content,
                        detail={
                            "version_id": result.get("version_id"),
                            "before_hash": result.get("before_hash"),
                            "after_hash": result.get("after_hash"),
                        },
                    ),
                )
            except Exception:
                pass
            return result

    def get_drama_resident(self, drama_id: str) -> str:
        self.store.ensure_drama_scaffold(drama_id)
        return self.store.read_text(self.store.drama_memory_dir(drama_id) / "MEMORY.md")

    def set_drama_resident(
        self,
        drama_id: str,
        content: str,
        *,
        skip_injection_scan: bool = False,
        actor: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        expected_version: Optional[str] = None,
    ) -> Dict[str, Any]:
        self.store.ensure_drama_scaffold(drama_id)
        if not skip_injection_scan:
            require_clean(content)
        if len(content) > 6000:
            raise ValueError("MEMORY.md 超过 6000 字符，请拆到 topics/ 或压缩不变量")
        with self.store.lock_for(drama_id):
            result = self._drama_vs(drama_id).commit(
                "memory",
                content,
                agent_id=actor or "",
                session_id=session_id or "",
                expected_version=expected_version,
            )
            self.append_audit(
                action="update",
                layer="resident",
                target_id="MEMORY.md",
                user_id=user_id,
                drama_id=drama_id,
                agent_id=actor,
                before=content,
                after=content,
                detail={
                    "version_id": result.get("version_id"),
                    "before_hash": result.get("before_hash"),
                    "after_hash": result.get("after_hash"),
                    "conflict": result.get("conflict"),
                },
            )
            return result

    def sync_user_profile_to_resident(self, user_id: str, profile: Dict[str, Any]) -> str:
        """从现有 UserProfile 同步到 USER.md（高密度）"""
        genres = ", ".join(profile.get("fav_genres") or []) or "（未设）"
        avoids = ", ".join(profile.get("avoid_tropes") or []) or "（未设）"
        styles = ", ".join(profile.get("language_style") or []) or "（未设）"
        content = f"""# USER — 用户常驻画像

> 自动同步自 UserProfile · {datetime.now().strftime('%Y-%m-%d')}

## 偏好题材
{genres}

## 回避桥段
{avoids}

## 语言风格
{styles}

## 沟通期待
- 先给可拍结构，再展开对白。
- 尊重已确认的人设与卡点计划。
"""
        self.set_user_resident(user_id, content)
        return content

    # ==================== L3 Episodic ====================

    def record_episode(self, episode: Episode) -> Episode:
        if not episode.drama_id:
            # 无作品时落到用户目录
            path = self.store.user_memory_dir(episode.user_id) / "episodes.jsonl"
            self.store.ensure_user_scaffold(episode.user_id)
        else:
            self.store.ensure_drama_scaffold(episode.drama_id)
            path = self.store.episode_day_path(episode.drama_id)
        self.store.append_jsonl(path, episode.to_dict())
        # 同步向量索引（指针级文本，不全文）
        if episode.drama_id:
            try:
                idx = MemoryVectorIndex(self.store.drama_memory_dir(episode.drama_id))
                blob = " ".join(
                    [
                        episode.task_description,
                        episode.approach,
                        episode.resolution,
                        " ".join(episode.tags),
                    ]
                )
                idx.upsert(
                    doc_id=f"ep:{episode.episode_id}",
                    text=blob,
                    layer="episodic",
                    metadata={
                        "outcome": episode.outcome,
                        "agent_id": episode.agent_id,
                        "session_id": episode.session_id,
                    },
                )
            except Exception as e:
                logger.debug("vector upsert episode: %s", e)
            self.append_audit(
                action="create",
                layer="episodic",
                target_id=episode.episode_id,
                user_id=episode.user_id,
                drama_id=episode.drama_id,
                agent_id=episode.agent_id,
                detail={"outcome": episode.outcome},
            )
        return episode

    def record_agent_turn(
        self,
        *,
        user_id: str,
        agent_id: str,
        task_description: str,
        outcome: str = EpisodeOutcome.SUCCESS.value,
        drama_id: Optional[str] = None,
        session_id: Optional[str] = None,
        approach: str = "",
        key_decisions: Optional[List[str]] = None,
        errors: Optional[List[str]] = None,
        resolution: str = "",
        tags: Optional[List[str]] = None,
        tokens_used: int = 0,
        duration_seconds: float = 0,
        user_feedback: Optional[str] = None,
    ) -> Episode:
        ep = Episode(
            episode_id=new_id("ep"),
            user_id=user_id,
            drama_id=drama_id,
            session_id=session_id,
            agent_id=agent_id,
            task_description=task_description[:800],
            approach=approach[:800],
            outcome=outcome,
            key_decisions=key_decisions or [],
            errors=errors or [],
            resolution=resolution[:800],
            user_feedback=user_feedback,
            tags=tags or [],
            tokens_used=tokens_used,
            duration_seconds=duration_seconds,
        )
        return self.record_episode(ep)

    def list_episodes(
        self,
        drama_id: str,
        *,
        limit: int = 50,
        agent_id: Optional[str] = None,
        outcome: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        self.store.ensure_drama_scaffold(drama_id)
        rows: List[Dict[str, Any]] = []
        for path in self.store.list_episode_files(drama_id):
            rows.extend(self.store.read_jsonl(path, limit=1000))
        if agent_id:
            rows = [r for r in rows if r.get("agent_id") == agent_id]
        if outcome:
            rows = [r for r in rows if r.get("outcome") == outcome]
        rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
        return rows[:limit]

    def get_episode(self, drama_id: str, episode_id: str) -> Optional[Dict[str, Any]]:
        for row in self.list_episodes(drama_id, limit=500):
            if row.get("episode_id") == episode_id:
                return row
        # 也查归档
        archive = self.store.drama_memory_dir(drama_id) / "episodes" / "_archive.jsonl"
        for row in self.store.read_jsonl(archive, limit=2000):
            if row.get("episode_id") == episode_id:
                return {**row, "_archived": True}
        return None

    def pin_episode(self, drama_id: str, episode_id: str, pinned: bool = True) -> bool:
        return self._mutate_episode(drama_id, episode_id, {"pinned": pinned})

    def soft_delete_episode(self, drama_id: str, episode_id: str, *, user_id: Optional[str] = None) -> bool:
        """软删除：移入 archive 并标 deleted。"""
        ep = self.get_episode(drama_id, episode_id)
        if not ep or ep.get("_archived"):
            # 若已在活动文件，下面 mutate 会处理
            pass
        ok = self._remove_episode_from_active(drama_id, episode_id, archive_extra={"deleted": True, "deleted_at": datetime.now().isoformat()})
        if ok:
            try:
                MemoryVectorIndex(self.store.drama_memory_dir(drama_id)).delete(f"ep:{episode_id}")
            except Exception:
                pass
            self.append_audit(
                action="delete",
                layer="episodic",
                target_id=episode_id,
                user_id=user_id,
                drama_id=drama_id,
                before=ep,
            )
        return ok

    def _mutate_episode(self, drama_id: str, episode_id: str, patch: Dict[str, Any]) -> bool:
        self.store.ensure_drama_scaffold(drama_id)
        for path in self.store.list_episode_files(drama_id):
            rows = self.store.read_jsonl(path, limit=5000)
            changed = False
            for row in rows:
                if row.get("episode_id") == episode_id:
                    row.update(patch)
                    changed = True
            if changed:
                path.write_text("".join(json_dumps_line(r) for r in rows), encoding="utf-8")
                return True
        return False

    def _remove_episode_from_active(
        self,
        drama_id: str,
        episode_id: str,
        *,
        archive_extra: Optional[Dict[str, Any]] = None,
    ) -> bool:
        archive_path = self.store.drama_memory_dir(drama_id) / "episodes" / "_archive.jsonl"
        for path in self.store.list_episode_files(drama_id):
            rows = self.store.read_jsonl(path, limit=5000)
            keep = []
            removed = None
            for row in rows:
                if row.get("episode_id") == episode_id:
                    removed = row
                else:
                    keep.append(row)
            if removed is not None:
                self.store.append_jsonl(archive_path, {**removed, **(archive_extra or {})})
                path.write_text("".join(json_dumps_line(r) for r in keep), encoding="utf-8")
                return True
        return False

    def search_episodes(
        self,
        drama_id: str,
        query: str,
        *,
        top_k: int = 5,
        use_vector: bool = True,
    ) -> List[Dict[str, Any]]:
        """关键词 + 向量融合召回；优先 pinned / failure。"""
        q = (query or "").lower().strip()
        tokens = [t for t in re.split(r"[\s,，。；;]+", q) if t]
        rows = self.list_episodes(drama_id, limit=300)
        by_id = {r.get("episode_id"): r for r in rows}

        def kw_score(row: Dict[str, Any]) -> float:
            blob = " ".join(
                [
                    str(row.get("task_description") or ""),
                    str(row.get("approach") or ""),
                    str(row.get("resolution") or ""),
                    " ".join(row.get("tags") or []),
                    " ".join(row.get("key_decisions") or []),
                    " ".join(row.get("errors") or []),
                ]
            ).lower()
            s = 0.0
            for t in tokens:
                if t in blob:
                    s += 2.0
            if row.get("pinned"):
                s += 3.0
            if row.get("outcome") == EpisodeOutcome.FAILURE.value:
                s += 1.5
            if row.get("agent_id") and row.get("agent_id") in q:
                s += 1.0
            return s

        scores: Dict[str, float] = {}
        for row in rows:
            eid = row.get("episode_id") or ""
            scores[eid] = kw_score(row)

        if use_vector and q:
            try:
                hits = MemoryVectorIndex(self.store.drama_memory_dir(drama_id)).search(
                    query, top_k=top_k * 2, layer="episodic"
                )
                for h in hits:
                    raw_id = (h.get("id") or "").replace("ep:", "", 1)
                    if raw_id in by_id:
                        scores[raw_id] = scores.get(raw_id, 0) + float(h.get("score") or 0) * 5.0
            except Exception as e:
                logger.debug("vector episode search: %s", e)

        ranked_ids = sorted(scores.keys(), key=lambda i: scores.get(i, 0), reverse=True)
        if tokens:
            ranked_ids = [i for i in ranked_ids if scores.get(i, 0) > 0] or ranked_ids[:top_k]
        return [by_id[i] for i in ranked_ids if i in by_id][:top_k]

    # ==================== L4 Semantic ====================

    def _semantic_path(self, drama_id: str) -> Path:
        return self.store.drama_memory_dir(drama_id) / "semantic.json"

    def _read_semantic(self, drama_id: str, path: Optional[Path] = None) -> List[Dict[str, Any]]:
        p = path or self._semantic_path(drama_id)
        data = self.store.read_json(p, {"facts": []})
        return data.get("facts") or []

    def _write_semantic(self, path: Path, facts: List[Dict[str, Any]]) -> None:
        self.store.write_json(path, {"schema_version": SCHEMA_VERSION, "facts": facts})

    def _touch(self, drama_id: str, fact_ids: List[str]) -> None:
        """召回加温：命中事实 access_count/strength/last_access（有上限，批量一次写回）。"""
        if not fact_ids:
            return
        with self.store.lock_for(drama_id):
            path = self._semantic_path(drama_id)
            facts = self._read_semantic(drama_id, path)
            by_id = {f.get("fact_id"): f for f in facts}
            changed = False
            now = datetime.now().isoformat()
            for fid in fact_ids:
                f = by_id.get(fid)
                if not f:
                    continue
                if int(f.get("access_count", 0)) >= 10_000:
                    continue
                f["access_count"] = int(f.get("access_count", 0)) + 1
                f["last_access"] = now
                f["strength"] = min(1.0, float(f.get("strength", 1.0)) + 0.01)
                changed = True
            if changed:
                self._write_semantic(path, facts)

    def list_facts(
        self,
        drama_id: str,
        *,
        active_only: bool = True,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        self.store.ensure_drama_scaffold(drama_id)
        data = self.store.read_json(self._semantic_path(drama_id), {"facts": []})
        facts = data.get("facts") or []
        if active_only:
            facts = [f for f in facts if f.get("status") == FactStatus.ACTIVE.value]
        if entity_type:
            facts = [f for f in facts if f.get("entity_type") == entity_type]
        if entity_id:
            facts = [f for f in facts if f.get("entity_id") == entity_id]
        return facts

    def upsert_fact(
        self,
        *,
        drama_id: str,
        entity_type: str,
        entity_id: str,
        predicate: str,
        value: Any,
        confidence: str = Confidence.FACT.value,
        user_id: Optional[str] = None,
        provenance: Optional[Dict[str, Any]] = None,
        pinned: bool = False,
        expected_version: Optional[int] = None,
    ) -> Dict[str, Any]:
        err = validate_fact(entity_type, predicate, value, entity_id=entity_id)
        if err:
            raise ValueError(err)

        self.store.ensure_drama_scaffold(drama_id)
        with self.store.lock_for(drama_id):
            head = self._semantic_head(drama_id)
            if expected_version is not None and expected_version != head:
                return self._conflict(expected_version, head)

            path = self._semantic_path(drama_id)
            data = self.store.read_json(path, {"facts": []})
            facts: List[Dict[str, Any]] = data.get("facts") or []

            # 同 key 活跃事实 → supersede（双时态：置 valid_until）
            key_match = [
                f
                for f in facts
                if f.get("entity_type") == entity_type
                and f.get("entity_id") == entity_id
                and f.get("predicate") == predicate
                and f.get("status") == FactStatus.ACTIVE.value
            ]

            exp_days = expires_days_for(predicate)
            expires_at = None
            if exp_days:
                expires_at = (datetime.now() + timedelta(days=exp_days)).isoformat()

            fact = SemanticFact(
                fact_id=new_id("fact"),
                entity_type=entity_type,
                entity_id=entity_id,
                predicate=predicate,
                value=value,
                confidence=confidence,
                status=FactStatus.ACTIVE.value,
                scope=default_scope_for(predicate),
                drama_id=drama_id,
                user_id=user_id,
                provenance=provenance or {"source": "agent", "created_at": datetime.now().isoformat()},
                expires_at=expires_at,
                pinned=pinned,
            )

            now = datetime.now().isoformat()
            for old in key_match:
                if str(old.get("value")) == str(value):
                    # 相同值：刷新时间 + 召回加温
                    old["updated_at"] = now
                    old["provenance"] = fact.provenance
                    old["strength"] = min(1.0, float(old.get("strength", 1.0)) + 0.1)
                    old["access_count"] = int(old.get("access_count", 0)) + 1
                    old["last_access"] = now
                    self._write_semantic(path, facts)
                    return old
                old["status"] = FactStatus.SUPERSEDED.value
                old["superseded_by"] = fact.fact_id
                old["updated_at"] = now
                old["valid_until"] = now  # 双时态：保留历史，标记失效时点

            facts.append(fact.to_dict())
            self._write_semantic(path, facts)
            self._bump_semantic_head(drama_id)
            try:
                idx = MemoryVectorIndex(self.store.drama_memory_dir(drama_id))
                idx.upsert(
                    doc_id=f"fact:{fact.fact_id}",
                    text=f"{entity_type}:{entity_id} {predicate}={value}",
                    layer="semantic",
                    metadata={"confidence": confidence, "predicate": predicate},
                )
            except Exception:
                pass
            self.append_audit(
                action="create",
                layer="semantic",
                target_id=fact.fact_id,
                user_id=user_id,
                drama_id=drama_id,
                after=fact.to_dict(),
            )
            return fact.to_dict()

    def update_fact(
        self,
        drama_id: str,
        fact_id: str,
        *,
        value: Any = None,
        confidence: Optional[str] = None,
        pinned: Optional[bool] = None,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
        expected_version: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        self.store.ensure_drama_scaffold(drama_id)
        with self.store.lock_for(drama_id):
            head = self._semantic_head(drama_id)
            if expected_version is not None and expected_version != head:
                return self._conflict(expected_version, head)
            path = self._semantic_path(drama_id)
            facts = self._read_semantic(drama_id, path)
            for f in facts:
                if f.get("fact_id") != fact_id:
                    continue
                before = dict(f)
                if value is not None:
                    f["value"] = value
                if confidence is not None:
                    f["confidence"] = confidence
                if pinned is not None:
                    f["pinned"] = pinned
                if status is not None:
                    f["status"] = status
                f["updated_at"] = datetime.now().isoformat()
                self._write_semantic(path, facts)
                self._bump_semantic_head(drama_id)
                self.append_audit(
                    action="update",
                    layer="semantic",
                    target_id=fact_id,
                    user_id=user_id,
                    drama_id=drama_id,
                    before=before,
                    after=f,
                )
                return f
        return None

    def delete_fact(
        self,
        drama_id: str,
        fact_id: str,
        *,
        user_id: Optional[str] = None,
        hard: bool = False,
        expected_version: Optional[int] = None,
    ) -> bool:
        self.store.ensure_drama_scaffold(drama_id)
        with self.store.lock_for(drama_id):
            head = self._semantic_head(drama_id)
            if expected_version is not None and expected_version != head:
                return False
            path = self._semantic_path(drama_id)
            facts = self._read_semantic(drama_id, path)
            target = next((f for f in facts if f.get("fact_id") == fact_id), None)
            if not target:
                return False
            if hard:
                facts = [f for f in facts if f.get("fact_id") != fact_id]
            else:
                target["status"] = FactStatus.ARCHIVED.value
                target["updated_at"] = datetime.now().isoformat()
                target["valid_until"] = datetime.now().isoformat()
                target["deleted"] = True
            self._write_semantic(path, facts)
            self._bump_semantic_head(drama_id)
            try:
                MemoryVectorIndex(self.store.drama_memory_dir(drama_id)).delete(f"fact:{fact_id}")
            except Exception:
                pass
            self.append_audit(
                action="delete",
                layer="semantic",
                target_id=fact_id,
                user_id=user_id,
                drama_id=drama_id,
                before=target,
                detail={"hard": hard},
            )
            return True

    def search_facts(
        self,
        drama_id: str,
        query: str,
        *,
        top_k: int = 12,
        use_vector: bool = True,
    ) -> List[Dict[str, Any]]:
        q = (query or "").lower()
        tokens = [t for t in re.split(r"[\s,，。；;]+", q) if t]
        facts = self.list_facts(drama_id, active_only=True)
        by_id = {f.get("fact_id"): f for f in facts}

        def score(f: Dict[str, Any]) -> float:
            blob = " ".join(
                [
                    str(f.get("entity_type") or ""),
                    str(f.get("entity_id") or ""),
                    str(f.get("predicate") or ""),
                    str(f.get("value") or ""),
                ]
            ).lower()
            s = sum(2.0 for t in tokens if t in blob)
            if f.get("pinned"):
                s += 2.0
            if f.get("predicate") in ("open_thread", "cliffhanger", "forbidden", "must_confirm"):
                s += 1.5
            return s

        scores: Dict[str, float] = {f.get("fact_id") or "": score(f) for f in facts}

        if use_vector and q.strip():
            try:
                hits = MemoryVectorIndex(self.store.drama_memory_dir(drama_id)).search(
                    query, top_k=top_k * 2, layer="semantic"
                )
                for h in hits:
                    raw_id = (h.get("id") or "").replace("fact:", "", 1)
                    if raw_id in by_id:
                        scores[raw_id] = scores.get(raw_id, 0) + float(h.get("score") or 0) * 5.0
            except Exception as e:
                logger.debug("vector fact search: %s", e)

        if not tokens and not q.strip():
            priority = [
                f
                for f in facts
                if f.get("pinned")
                or f.get("predicate")
                in ("open_thread", "cliffhanger", "forbidden", "must_confirm", "world_invariant")
            ]
            result = (priority or facts)[:top_k]
            self._touch(drama_id, [f.get("fact_id") for f in result if f.get("fact_id")])
            return result

        ranked_ids = sorted(scores.keys(), key=lambda i: scores.get(i, 0), reverse=True)
        ranked_ids = [i for i in ranked_ids if scores.get(i, 0) > 0] or ranked_ids[:top_k]
        result = [by_id[i] for i in ranked_ids if i in by_id][:top_k]
        self._touch(drama_id, [f.get("fact_id") for f in result if f.get("fact_id")])
        return result

    # ==================== L5 Procedural ====================

    def _skills_path(self, drama_id: str) -> Path:
        return self.store.drama_memory_dir(drama_id) / "skills.json"

    def _read_skills(self, drama_id: str, path: Optional[Path] = None) -> List[Dict[str, Any]]:
        p = path or self._skills_path(drama_id)
        data = self.store.read_json(p, {"skills": []})
        return data.get("skills") or []

    def _write_skills(self, path: Path, skills: List[Dict[str, Any]]) -> None:
        self.store.write_json(path, {"schema_version": SCHEMA_VERSION, "skills": skills})

    def list_promoted_skills(
        self,
        drama_id: str,
        *,
        enabled_only: bool = True,
    ) -> List[Dict[str, Any]]:
        self.store.ensure_drama_scaffold(drama_id)
        data = self.store.read_json(self._skills_path(drama_id), {"skills": []})
        skills = data.get("skills") or []
        if enabled_only:
            return [s for s in skills if s.get("enabled", True)]
        return skills

    def promote_skill_from_episodes(
        self,
        drama_id: str,
        *,
        name: str,
        trigger: str,
        min_success: int = 3,
        agent_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """同一类成功任务达到阈值后晋升为技能。"""
        rows = self.list_episodes(drama_id, limit=200, agent_id=agent_id, outcome=EpisodeOutcome.SUCCESS.value)
        matched = [
            r
            for r in rows
            if trigger.lower() in (r.get("task_description") or "").lower()
            or trigger.lower() in " ".join(r.get("tags") or []).lower()
        ]
        if len(matched) < min_success:
            return None

        steps = []
        for r in matched[:5]:
            if r.get("approach"):
                steps.append(r["approach"][:200])
            elif r.get("resolution"):
                steps.append(r["resolution"][:200])
        steps = list(dict.fromkeys(steps))[:8]

        skill = SkillRecord(
            skill_id=new_id("skill"),
            name=name,
            trigger=trigger,
            steps=steps or [f"参考历史成功路径：{name}"],
            success_criteria="任务 outcome=success 且无关键错误",
            failure_modes=[
                e
                for r in self.list_episodes(drama_id, limit=50, outcome=EpisodeOutcome.FAILURE.value)
                for e in (r.get("errors") or [])
                if trigger.lower() in (r.get("task_description") or "").lower()
            ][:5],
            success_count=len(matched),
            success_rate=1.0,
            source_episode_ids=[r.get("episode_id") for r in matched[:10] if r.get("episode_id")],
            drama_id=drama_id,
            last_used=datetime.now().isoformat(),
        )
        path = self._skills_path(drama_id)
        with self.store.lock_for(drama_id):
            skills = self._read_skills(drama_id, path)
            # 同名覆盖版本
            for old in skills:
                if old.get("name") == name:
                    old["enabled"] = False
                    skill.version = int(old.get("version") or 1) + 1
            skills.append(skill.to_dict())
            self._write_skills(path, skills)
            self.append_audit(
                action="promote",
                layer="procedural",
                target_id=skill.skill_id,
                drama_id=drama_id,
                after=skill.to_dict(),
            )
        return skill.to_dict()

    def set_skill_enabled(
        self,
        drama_id: str,
        skill_id: str,
        enabled: bool,
        *,
        user_id: Optional[str] = None,
    ) -> bool:
        path = self._skills_path(drama_id)
        with self.store.lock_for(drama_id):
            skills = self._read_skills(drama_id, path)
            for s in skills:
                if s.get("skill_id") == skill_id:
                    s["enabled"] = enabled
                    s["updated_at"] = datetime.now().isoformat()
                    self._write_skills(path, skills)
                    self.append_audit(
                        action="update",
                        layer="procedural",
                        target_id=skill_id,
                        user_id=user_id,
                        drama_id=drama_id,
                        detail={"enabled": enabled},
                    )
                    return True
        return False

    def delete_skill(self, drama_id: str, skill_id: str, *, user_id: Optional[str] = None) -> bool:
        path = self._skills_path(drama_id)
        with self.store.lock_for(drama_id):
            skills = self._read_skills(drama_id, path)
            before = next((s for s in skills if s.get("skill_id") == skill_id), None)
            if not before:
                return False
            skills = [s for s in skills if s.get("skill_id") != skill_id]
            self._write_skills(path, skills)
            self.append_audit(
                action="delete",
                layer="procedural",
                target_id=skill_id,
                user_id=user_id,
                drama_id=drama_id,
                before=before,
            )
            return True

    # ==================== Reflection ====================

    def record_reflection(
        self,
        *,
        drama_id: str,
        user_id: str,
        kind: str,
        summary: str,
        episode_id: Optional[str] = None,
        why: Optional[List[str]] = None,
        next_action: str = "",
    ) -> Dict[str, Any]:
        self.store.ensure_drama_scaffold(drama_id)
        ref = Reflection(
            reflection_id=new_id("ref"),
            drama_id=drama_id,
            user_id=user_id,
            episode_id=episode_id,
            kind=kind,
            summary=summary[:500],
            why=why or [],
            next_action=next_action[:300],
        )
        self.store.append_jsonl(self.store.reflections_path(drama_id), ref.to_dict())
        self.append_audit(
            action="reflect",
            layer="episodic",
            target_id=ref.reflection_id,
            user_id=user_id,
            drama_id=drama_id,
            detail={"kind": kind, "episode_id": episode_id},
        )
        return ref.to_dict()

    def list_reflections(self, drama_id: str, *, limit: int = 50) -> List[Dict[str, Any]]:
        self.store.ensure_drama_scaffold(drama_id)
        rows = self.store.read_jsonl(self.store.reflections_path(drama_id), limit=500)
        rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
        return rows[:limit]

    def reflect_on_episode(
        self,
        drama_id: str,
        episode_id: str,
        *,
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        ep = self.get_episode(drama_id, episode_id)
        if not ep:
            return None
        outcome = ep.get("outcome") or "partial"
        if outcome == "failure":
            summary = f"失败: {(ep.get('task_description') or '')[:80]}"
            why = list(ep.get("errors") or [])[:5] or [str(ep.get("resolution") or "")[:120]]
            next_action = "避开同类错误；必要时更新 RULES / forbidden"
        elif outcome == "success":
            summary = f"成功: {(ep.get('task_description') or '')[:80]}"
            why = list(ep.get("key_decisions") or [])[:5] or [str(ep.get("approach") or "")[:120]]
            next_action = "可考虑晋升为 procedural skill"
        else:
            summary = f"部分完成: {(ep.get('task_description') or '')[:80]}"
            why = list(ep.get("key_decisions") or [])[:3]
            next_action = "补齐未完成步骤后再写入事实"
        return self.record_reflection(
            drama_id=drama_id,
            user_id=user_id or ep.get("user_id") or "system",
            episode_id=episode_id,
            kind=outcome,
            summary=summary,
            why=[w for w in why if w],
            next_action=next_action,
        )

    # ==================== Audit / Evidence / Slice ====================

    def append_audit(
        self,
        *,
        action: str,
        layer: str,
        target_id: str,
        user_id: Optional[str] = None,
        drama_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        detail: Optional[Dict[str, Any]] = None,
        before: Any = None,
        after: Any = None,
    ) -> None:
        if not drama_id:
            return
        try:
            self.store.ensure_drama_scaffold(drama_id)
            self.store.append_jsonl(
                self.store.audit_path(drama_id),
                audit_entry(
                    action=action,
                    layer=layer,
                    target_id=target_id,
                    user_id=user_id,
                    drama_id=drama_id,
                    agent_id=agent_id,
                    detail=detail,
                    before=before,
                    after=after,
                ),
            )
        except Exception as e:
            logger.debug("audit append: %s", e)

    def list_audit(self, drama_id: str, *, limit: int = 100) -> List[Dict[str, Any]]:
        self.store.ensure_drama_scaffold(drama_id)
        rows = self.store.read_jsonl(self.store.audit_path(drama_id), limit=1000)
        rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
        return rows[:limit]

    def write_evidence(
        self,
        drama_id: str,
        content: str,
        *,
        evidence_id: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """原文落盘，常驻只存指针。"""
        self.store.ensure_drama_scaffold(drama_id)
        eid = evidence_id or new_id("ev")
        path = self.store.evidence_path(drama_id, eid)
        header = f"<!-- evidence {eid} {json_dumps_line(meta or {}).strip()} -->\n"
        self.store.write_text(path, header + content)
        return evidence_ref(kind="file", path=str(path), quote=content[:120])

    def read_memory_slice(
        self,
        drama_id: str,
        *,
        relative_path: str,
        offset: int = 0,
        length: int = 2000,
    ) -> Dict[str, Any]:
        """局部读取 topics/evidence/episodes 等，避免全量进上下文。"""
        base = self.store.drama_memory_dir(drama_id).resolve()
        target = (base / relative_path).resolve()
        if not str(target).startswith(str(base)):
            raise ValueError("路径越界")
        if not target.exists():
            raise FileNotFoundError(relative_path)
        chunk = self.store.read_slice(target, offset=offset, length=length)
        return {
            "path": relative_path,
            "offset": offset,
            "length": length,
            "chars": len(chunk),
            "content": chunk,
            "truncated": len(chunk) >= length,
        }

    def list_topics(self, drama_id: str) -> List[str]:
        topics = self.store.drama_memory_dir(drama_id) / "topics"
        if not topics.exists():
            return []
        return sorted(p.name for p in topics.glob("*.md"))

    # ==================== Vector / Dream ====================

    def rebuild_vector_index(self, drama_id: str) -> Dict[str, Any]:
        self.store.ensure_drama_scaffold(drama_id)
        idx = MemoryVectorIndex(self.store.drama_memory_dir(drama_id))
        return idx.rebuild_from_rows(
            episodes=self.list_episodes(drama_id, limit=500),
            facts=self.list_facts(drama_id, active_only=False),
        )

    def vector_search(
        self,
        drama_id: str,
        query: str,
        *,
        top_k: int = 8,
        layer: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        self.store.ensure_drama_scaffold(drama_id)
        return MemoryVectorIndex(self.store.drama_memory_dir(drama_id)).search(
            query, top_k=top_k, layer=layer
        )

    def run_dream(
        self,
        drama_id: str,
        *,
        user_id: Optional[str] = None,
        auto_promote: bool = True,
        compress_resident: bool = True,
    ) -> Dict[str, Any]:
        from .dreaming import run_dream

        return run_dream(
            self,
            drama_id,
            user_id=user_id,
            auto_promote=auto_promote,
            compress_resident=compress_resident,
        )

    def build_procedural_block(self, drama_id: Optional[str], *, max_chars: int = 2500) -> str:
        """合并全局 skills 名录（渐进式披露）+ 作品晋升技能摘要。"""
        from utils.skill_loader import build_skills_prompt

        # 默认只注入名录，完整正文靠 load_skill / skill_search
        parts = [
            build_skills_prompt(
                enabled_only=True,
                max_chars=max_chars // 2,
                mode="catalog",
                compact=True,
            )
        ]
        if drama_id:
            promoted = self.list_promoted_skills(drama_id)
            if promoted:
                lines = ["### 作品沉淀技能（摘要）", "完整步骤可 memory_promote_skill / skill_search 查看。"]
                for s in promoted[:5]:
                    lines.append(f"- **{s.get('name')}** · trigger: {s.get('trigger')}")
                    for step in (s.get("steps") or [])[:2]:
                        lines.append(f"  - {step}")
                parts.append("\n".join(lines))
        text = "\n\n".join(p for p in parts if p and p.strip())
        return text[:max_chars]

    # ==================== Forgetting ====================

    def run_forgetting(
        self,
        drama_id: str,
        *,
        episodic_ttl_days: int = 90,
        routine_ttl_days: int = 30,
    ) -> Dict[str, Any]:
        """
        三类操作：
        1) Expiration — 过期情节归档 / 过期语义失效
        2) Supersession — 已由 upsert 处理
        3) Contradiction flag — 同 predicate 多 active（异常）
        """
        self.store.ensure_drama_scaffold(drama_id)
        now = datetime.now()
        archived_eps = 0
        expired_facts = 0
        decayed_facts = 0
        flagged = 0

        # episodes: 非 pinned 且超 TTL → 移到 archive jsonl
        archive_path = self.store.drama_memory_dir(drama_id) / "episodes" / "_archive.jsonl"
        for path in self.store.list_episode_files(drama_id):
            if path.name.startswith("_"):
                continue
            keep: List[Dict[str, Any]] = []
            for row in self.store.read_jsonl(path, limit=5000):
                if row.get("pinned"):
                    keep.append(row)
                    continue
                try:
                    created = datetime.fromisoformat(row.get("created_at") or now.isoformat())
                except Exception:
                    created = now
                age = (now - created).days
                ttl = routine_ttl_days if row.get("outcome") == EpisodeOutcome.SUCCESS.value else episodic_ttl_days
                if age > ttl:
                    self.store.append_jsonl(archive_path, {**row, "archived_at": now.isoformat()})
                    archived_eps += 1
                else:
                    keep.append(row)
            # 重写当日文件
            path.write_text(
                "".join(json_dumps_line(r) for r in keep),
                encoding="utf-8",
            )

        # semantic: 强度衰减 + TTL 过期 + contradiction
        path = self._semantic_path(drama_id)
        facts = self._read_semantic(drama_id, path)
        active_keys: Dict[str, List[Dict[str, Any]]] = {}
        for f in facts:
            if f.get("status") != FactStatus.ACTIVE.value:
                continue
            if f.get("pinned"):
                continue

            # 强度衰减（Ebbinghaus 式 R(t)=e^(-t/S)，S 由 predicate 重要度决定）
            try:
                created = datetime.fromisoformat(f.get("valid_from") or f.get("created_at") or now.isoformat())
            except Exception:
                created = now
            age_days = max(0, (now - created).days)
            s = strength_s_for(f.get("predicate") or "")
            strength = float(f.get("strength", 1.0))
            if s > 0:
                strength = strength * math.exp(-age_days / s)
            f["strength"] = round(strength, 4)
            if strength < STRENGTH_FLOOR:
                f["status"] = FactStatus.ARCHIVED.value
                f["valid_until"] = now.isoformat()
                f["updated_at"] = now.isoformat()
                decayed_facts += 1
                continue

            exp = f.get("expires_at")
            if exp:
                try:
                    if datetime.fromisoformat(exp) < now:
                        f["status"] = FactStatus.ARCHIVED.value
                        f["valid_until"] = now.isoformat()
                        f["updated_at"] = now.isoformat()
                        expired_facts += 1
                        continue
                except Exception:
                    pass
            key = f"{f.get('entity_type')}|{f.get('entity_id')}|{f.get('predicate')}"
            active_keys.setdefault(key, []).append(f)

        for key, group in active_keys.items():
            if len(group) > 1:
                # 保留最新，其余 flag
                group.sort(key=lambda x: x.get("updated_at") or x.get("created_at") or "", reverse=True)
                for old in group[1:]:
                    old["status"] = FactStatus.FLAGGED.value
                    old["updated_at"] = now.isoformat()
                    flagged += 1

        self._write_semantic(path, facts)
        return {
            "archived_episodes": archived_eps,
            "expired_facts": expired_facts,
            "decayed_facts": decayed_facts,
            "flagged_contradictions": flagged,
            "ran_at": now.isoformat(),
        }

    # ==================== Working Memory Assembler ====================

    def assemble_working_memory(
        self,
        *,
        user_id: str,
        drama_id: Optional[str],
        query: str = "",
        bible: str = "",
        budget_chars: int = 8000,
        include_rules: bool = True,
        include_resident: bool = True,
        include_episodic: bool = True,
        include_semantic: bool = True,
        include_procedural: bool = True,
        episodic_k: int = 4,
        semantic_k: int = 10,
    ) -> WorkingMemoryBundle:
        """
        按预算组装工作记忆。常驻/规则优先，其次语义治理事实，再情节召回，最后技能。
        """
        try:
            from utils.memory_settings import get_memory_settings_manager

            settings = get_memory_settings_manager().get_settings(user_id, drama_id)
            if not settings.effective_enabled:
                return WorkingMemoryBundle()
        except Exception:
            pass

        if drama_id:
            self.ensure(user_id=user_id, drama_id=drama_id)
        else:
            self.ensure(user_id=user_id)

        bundle = WorkingMemoryBundle()
        used = 0

        def take(text: str, soft_cap: int) -> str:
            nonlocal used
            remain = budget_chars - used
            if remain <= 0 or not text:
                return ""
            chunk = text[: min(soft_cap, remain)]
            used += len(chunk)
            return chunk

        if include_rules and drama_id:
            bundle.rules = take(self.get_rules(drama_id), 1800)
        if include_resident:
            user_md = self.get_user_resident(user_id)
            drama_md = self.get_drama_resident(drama_id) if drama_id else ""
            resident = ""
            if user_md.strip():
                resident += "### USER\n" + user_md.strip()[:1500] + "\n"
            if drama_md.strip():
                resident += "### DRAMA MEMORY\n" + drama_md.strip()[:2000] + "\n"
            if drama_id:
                try:
                    org_md = self.get_org_resident()
                    if org_md.strip():
                        resident += "### ORG\n" + org_md.strip()[:1200]
                except Exception:
                    pass
            bundle.resident = take(resident, 2800)
        if bible:
            bundle.bible = take(bible, 3000)
        if include_semantic and drama_id:
            bundle.semantic_hits = self.search_facts(drama_id, query, top_k=semantic_k)
            used += sum(len(str(f.get("value") or "")) + 40 for f in bundle.semantic_hits)
        if include_episodic and drama_id:
            bundle.episodic_hits = self.search_episodes(drama_id, query, top_k=episodic_k)
            used += sum(len(str(e.get("task_description") or "")) for e in bundle.episodic_hits)
        if include_procedural:
            proc = self.build_procedural_block(drama_id, max_chars=min(2500, max(400, budget_chars - used)))
            bundle.procedural = take(proc, 2500)

        bundle.total_chars = used
        bundle.truncated = used >= budget_chars * 0.95
        return bundle

    def overview(self, user_id: str, drama_id: Optional[str] = None) -> Dict[str, Any]:
        self.ensure(user_id=user_id, drama_id=drama_id)
        out: Dict[str, Any] = {
            "layers": {
                "rules": "作品 RULES.md — 必须遵守的工作宪法",
                "resident": "USER.md + MEMORY.md — 短硬常驻画像",
                "episodic": "episodes/*.jsonl — 任务过程与结果",
                "semantic": "semantic.json — 本体约束的事实+证据",
                "procedural": "skills/*.md + memory/skills.json — 可复用方法",
                "forgetting": "TTL / supersede / contradiction flag",
            },
            "ontology": ontology_schema(),
            "user": {
                "path": str(self.store.user_memory_dir(user_id)),
                "user_md_chars": len(self.get_user_resident(user_id)),
            },
        }
        if drama_id:
            facts = self.list_facts(drama_id, active_only=False)
            active = [f for f in facts if f.get("status") == FactStatus.ACTIVE.value]
            flagged = [f for f in facts if f.get("status") == FactStatus.FLAGGED.value]
            superseded = [f for f in facts if f.get("status") == FactStatus.SUPERSEDED.value]
            eps = self.list_episodes(drama_id, limit=500)
            reflections = self.list_reflections(drama_id, limit=500)
            avg_strength = round(sum(float(f.get("strength", 1.0)) for f in active) / len(active), 3) if active else 0.0
            total_access = sum(int(f.get("access_count", 0)) for f in facts)
            out["drama"] = {
                "drama_id": drama_id,
                "path": str(self.store.drama_memory_dir(drama_id)),
                "rules_chars": len(self.get_rules(drama_id)),
                "memory_md_chars": len(self.get_drama_resident(drama_id)),
                "episodes": len(eps),
                "facts_active": len(active),
                "facts_flagged": len(flagged),
                "facts_superseded": len(superseded),
                "facts_total": len(facts),
                "avg_strength": avg_strength,
                "total_access": total_access,
                "schema_version": int(self.store.read_meta(drama_id).get("schema_version") or SCHEMA_VERSION),
                "head_version": self._semantic_head(drama_id),
                "promoted_skills": len(self.list_promoted_skills(drama_id)),
                "reflections": len(reflections),
                "topics": self.list_topics(drama_id),
                "architecture": {
                    "resident": "短索引常驻上下文",
                    "history": "episodes/semantic 可搜可局部读，不全量注入",
                    "recall": "关键词+向量 ANN",
                    "reflection": "reflections.jsonl 绑 episode",
                    "skill_extraction": "promote_skill_from_episodes + dreaming",
                    "dreaming": "run_dream 离线整理",
                    "governance": "provenance / TTL / confidence / audit / injection scan",
                },
            }
        return out

    # ==================== User-level semantic (style examples) ====================

    def _user_semantic_path(self, user_id: str) -> Path:
        return self.store.user_memory_dir(user_id) / "semantic.json"

    def record_user_style_example(self, user_id: str, text: str, *, source: str = "style_edit") -> Dict[str, Any]:
        """把风格示例落为用户级语义事实（predicate=style_example），替代旧 StyleMemory 持久化。"""
        self.store.ensure_user_scaffold(user_id)
        text = (text or "").strip()
        if not text:
            return {}
        with self.store.lock_for(f"user:{user_id}"):
            path = self._user_semantic_path(user_id)
            data = self.store.read_json(path, {"facts": []})
            facts = data.get("facts") or []
            fact = SemanticFact(
                fact_id=new_id("stylefact"),
                entity_type="style",
                entity_id=user_id,
                predicate="style_example",
                value=text[:2000],
                confidence=Confidence.PREFERENCE.value,
                scope="user",
                user_id=user_id,
                provenance={"source": source, "created_at": datetime.now().isoformat()},
            )
            facts.append(fact.to_dict())
            self.store.write_json(path, {"schema_version": SCHEMA_VERSION, "facts": facts})
            return fact.to_dict()

    def list_user_style_examples(self, user_id: str, *, limit: int = 20) -> List[Dict[str, Any]]:
        self.store.ensure_user_scaffold(user_id)
        data = self.store.read_json(self._user_semantic_path(user_id), {"facts": []})
        facts = [f for f in (data.get("facts") or []) if f.get("predicate") == "style_example"]
        facts.sort(key=lambda f: f.get("created_at") or "", reverse=True)
        return facts[:limit]

    # ==================== Version chain (markdown targets) ====================

    def list_memory_versions(self, drama_id: str, target: Optional[str] = None) -> List[Dict[str, Any]]:
        self.store.ensure_drama_scaffold(drama_id)
        return self._drama_vs(drama_id).list_versions(target=target)

    def get_memory_version(self, drama_id: str, version_id: str) -> Optional[Dict[str, Any]]:
        self.store.ensure_drama_scaffold(drama_id)
        return self._drama_vs(drama_id).get_version(version_id)

    def diff_memory_version(self, drama_id: str, version_id: str) -> str:
        self.store.ensure_drama_scaffold(drama_id)
        return self._drama_vs(drama_id).diff(version_id)

    def rollback_memory_version(
        self,
        drama_id: str,
        version_id: str,
        *,
        agent_id: str = "",
        session_id: str = "",
    ) -> Dict[str, Any]:
        with self.store.lock_for(drama_id):
            result = self._drama_vs(drama_id).rollback(version_id, agent_id=agent_id, session_id=session_id)
        if result.get("changed"):
            self.append_audit(
                action="rollback",
                layer="resident",
                target_id=version_id,
                drama_id=drama_id,
                detail={"version_id": result.get("version_id"), "from": version_id},
            )
        return result

    def list_org_versions(self) -> List[Dict[str, Any]]:
        self.store.ensure_org_scaffold()
        return self._org_vs().list_versions()

    # ==================== Org-level shared memory ====================

    def _org_semantic_path(self) -> Path:
        return self.store.org_memory_dir() / "semantic.json"

    def _read_org_facts(self) -> List[Dict[str, Any]]:
        data = self.store.read_json(self._org_semantic_path(), {"facts": []})
        return data.get("facts") or []

    def _write_org_facts(self, facts: List[Dict[str, Any]]) -> None:
        self.store.write_json(self._org_semantic_path(), {"schema_version": SCHEMA_VERSION, "facts": facts})

    def get_org_resident(self) -> str:
        self.store.ensure_org_scaffold()
        return self.store.read_text(self.store.org_memory_dir() / "ORG.md")

    def set_org_resident(
        self,
        content: str,
        *,
        actor: Optional[str] = None,
        session_id: Optional[str] = None,
        expected_version: Optional[str] = None,
    ) -> Dict[str, Any]:
        self.store.ensure_org_scaffold()
        require_clean(content)
        if len(content) > 6000:
            raise ValueError("ORG.md 超过 6000 字符，请压缩")
        with self.store.lock_for("org"):
            result = self._org_vs().commit(
                "org",
                content,
                agent_id=actor or "",
                session_id=session_id or "",
                expected_version=expected_version,
            )
            self.store.append_jsonl(
                self.store.org_memory_dir() / "audit.jsonl",
                audit_entry(
                    action="update",
                    layer="resident",
                    target_id="ORG.md",
                    agent_id=actor,
                    detail={
                        "version_id": result.get("version_id"),
                        "before_hash": result.get("before_hash"),
                        "after_hash": result.get("after_hash"),
                    },
                ),
            )
            return result

    def list_org_facts(self, active_only: bool = False) -> List[Dict[str, Any]]:
        self.store.ensure_org_scaffold()
        facts = self._read_org_facts()
        if active_only:
            facts = [f for f in facts if f.get("status") == FactStatus.ACTIVE.value]
        return facts

    def upsert_org_fact(
        self,
        *,
        entity_type: str,
        entity_id: str,
        predicate: str,
        value: Any,
        confidence: str = Confidence.FACT.value,
        provenance: Optional[Dict[str, Any]] = None,
        pinned: bool = False,
    ) -> Dict[str, Any]:
        err = validate_fact(entity_type, predicate, value, entity_id=entity_id)
        if err:
            raise ValueError(err)
        self.store.ensure_org_scaffold()
        with self.store.lock_for("org"):
            facts = self._read_org_facts()
            key_match = [
                f
                for f in facts
                if f.get("entity_type") == entity_type
                and f.get("entity_id") == entity_id
                and f.get("predicate") == predicate
                and f.get("status") == FactStatus.ACTIVE.value
            ]
            fact = SemanticFact(
                fact_id=new_id("orgfact"),
                entity_type=entity_type,
                entity_id=entity_id,
                predicate=predicate,
                value=value,
                confidence=confidence,
                status=FactStatus.ACTIVE.value,
                scope="org",
                provenance=provenance or {"source": "agent", "created_at": datetime.now().isoformat()},
                pinned=pinned,
            )
            now = datetime.now().isoformat()
            for old in key_match:
                if str(old.get("value")) == str(value):
                    old["updated_at"] = now
                    old["provenance"] = fact.provenance
                    self._write_org_facts(facts)
                    return old
                old["status"] = FactStatus.SUPERSEDED.value
                old["superseded_by"] = fact.fact_id
                old["updated_at"] = now
                old["valid_until"] = now
            facts.append(fact.to_dict())
            self._write_org_facts(facts)
            self.store.append_jsonl(
                self.store.org_memory_dir() / "audit.jsonl",
                audit_entry(action="create", layer="semantic", target_id=fact.fact_id, after=fact.to_dict()),
            )
            return fact.to_dict()

    def search_org(self, query: str, *, top_k: int = 8) -> List[Dict[str, Any]]:
        q = (query or "").lower()
        tokens = [t for t in re.split(r"[\s,，。；;]+", q) if t]
        facts = self.list_org_facts(active_only=True)

        def score(f: Dict[str, Any]) -> float:
            blob = " ".join([str(f.get(k) or "") for k in ("entity_type", "entity_id", "predicate", "value")]).lower()
            return sum(2.0 for t in tokens if t in blob)

        if not tokens:
            return facts[:top_k]
        scored = sorted(facts, key=score, reverse=True)
        return [f for f in scored if score(f) > 0][:top_k]

    def run_org_dream(self) -> Dict[str, Any]:
        from .dreaming import run_org_dream

        return run_org_dream(self)

    # ==================== Export / Redact ====================

    def export_memory(self, drama_id: str) -> Dict[str, Any]:
        self.store.ensure_drama_scaffold(drama_id)
        return {
            "schema_version": SCHEMA_VERSION,
            "drama_id": drama_id,
            "exported_at": datetime.now().isoformat(),
            "meta": self.store.read_meta(drama_id),
            "rules": self.get_rules(drama_id),
            "resident": self.get_drama_resident(drama_id),
            "facts": self.list_facts(drama_id, active_only=False),
            "episodes": self.list_episodes(drama_id, limit=2000),
            "skills": self.list_promoted_skills(drama_id, enabled_only=False),
            "reflections": self.list_reflections(drama_id, limit=2000),
            "audit": self.list_audit(drama_id, limit=2000),
            "versions": self._drama_vs(drama_id).list_versions(),
        }

    def redact_memory(self, drama_id: str, *, preview: bool = True) -> Dict[str, Any]:
        data = self.export_memory(drama_id)
        text = json.dumps(data, ensure_ascii=False, default=str)
        hits: List[Dict[str, Any]] = []
        for name, pattern in _PII_PATTERNS:
            for m in pattern.finditer(text):
                hits.append({"type": name, "match": m.group(0), "start": m.start(), "end": m.end()})
        redacted = text
        for name, pattern in _PII_PATTERNS:
            redacted = pattern.sub("[REDACTED]", redacted)
        result: Dict[str, Any] = {"hits": hits, "count": len(hits), "preview": preview}
        if preview:
            result["redacted_text"] = redacted
        else:
            out_path = self.store.drama_memory_dir(drama_id) / "redacted_export.json"
            self.store.write_text(out_path, redacted)
            result["written_to"] = str(out_path)
        self.append_audit(
            action="redact",
            layer="working",
            target_id=drama_id,
            drama_id=drama_id,
            detail={"count": len(hits), "preview": preview},
        )
        return result


_PII_PATTERNS: List[tuple] = [
    ("email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("phone_cn", re.compile(r"\b1[3-9]\d{9}\b")),
    ("id_card_cn", re.compile(r"\b\d{17}[\dXx]\b|\b\d{15}\b")),
    ("name", re.compile(r"(?:姓名|名字|用户)\s*[:：]\s*[\u4e00-\u9fff]{2,4}")),
]


def json_dumps_line(obj: Dict[str, Any]) -> str:
    import json

    return json.dumps(obj, ensure_ascii=False) + "\n"


_service: Optional[AgentMemoryService] = None


def get_agent_memory_service() -> AgentMemoryService:
    global _service
    if _service is None:
        _service = AgentMemoryService()
    return _service
