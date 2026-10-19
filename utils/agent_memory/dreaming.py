"""
Dreaming — 空闲离线整理（非在线 turn 塞上下文）

借鉴 MemGPT / Letta "sleep-time compute" 与 Mem0 consolidation:
1. 运行遗忘引擎（TTL / 矛盾）
2. 从成功情节提炼 lesson → semantic lesson_learned
3. 压缩 / 刷新 MEMORY.md 索引页（只保留不变量 + 下一轮）
4. 达到阈值的成功路径自动晋升技能
5. 重建向量索引

调用方: API / cron / memory_curator tool — 绝不在每轮 chat 同步跑重活。
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def run_dream(
    service: Any,
    drama_id: str,
    *,
    user_id: Optional[str] = None,
    auto_promote: bool = True,
    promote_min_success: int = 3,
    compress_resident: bool = True,
) -> Dict[str, Any]:
    """对单部作品执行一轮 dreaming。"""
    started = datetime.now().isoformat()
    report: Dict[str, Any] = {
        "drama_id": drama_id,
        "started_at": started,
        "forgetting": None,
        "lessons_written": 0,
        "skills_promoted": [],
        "resident_updated": False,
        "vector_rebuilt": None,
        "reflections": 0,
    }

    # 1) forgetting
    try:
        report["forgetting"] = service.run_forgetting(drama_id)
    except Exception as e:
        logger.warning("dream forgetting: %s", e)
        report["forgetting"] = {"error": str(e)}

    # 2) reflections + lessons from failures/successes
    try:
        eps = service.list_episodes(drama_id, limit=100)
        failures = [e for e in eps if e.get("outcome") == "failure"]
        successes = [e for e in eps if e.get("outcome") == "success"]

        for ep in failures[:8]:
            lesson = _lesson_from_episode(ep, kind="failure")
            if lesson:
                service.upsert_fact(
                    drama_id=drama_id,
                    entity_type="decision",
                    entity_id=ep.get("episode_id") or "ep",
                    predicate="lesson_learned",
                    value=lesson,
                    confidence="inference",
                    user_id=user_id,
                    provenance={
                        "source": "dreaming",
                        "episode_id": ep.get("episode_id"),
                        "session_id": ep.get("session_id"),
                        "created_at": datetime.now().isoformat(),
                    },
                )
                report["lessons_written"] += 1
                try:
                    service.record_reflection(
                        drama_id=drama_id,
                        user_id=user_id or ep.get("user_id") or "system",
                        episode_id=ep.get("episode_id"),
                        kind="failure",
                        summary=lesson,
                        why=ep.get("errors") or [],
                        next_action="下一轮避开同类错误",
                    )
                    report["reflections"] += 1
                except Exception:
                    pass

        for ep in successes[:5]:
            if not (ep.get("approach") or ep.get("key_decisions")):
                continue
            lesson = _lesson_from_episode(ep, kind="success")
            if lesson:
                try:
                    service.record_reflection(
                        drama_id=drama_id,
                        user_id=user_id or ep.get("user_id") or "system",
                        episode_id=ep.get("episode_id"),
                        kind="success",
                        summary=lesson,
                        why=ep.get("key_decisions") or [],
                        next_action="可晋升为 procedural skill",
                    )
                    report["reflections"] += 1
                except Exception:
                    pass
    except Exception as e:
        logger.warning("dream lessons: %s", e)

    # 3) compress resident MEMORY.md into short index
    if compress_resident:
        try:
            report["resident_updated"] = _refresh_memory_index(service, drama_id)
        except Exception as e:
            logger.warning("dream resident: %s", e)

    # 4) auto promote skills by common tags/triggers
    if auto_promote:
        try:
            report["skills_promoted"] = _auto_promote(service, drama_id, min_success=promote_min_success)
        except Exception as e:
            logger.warning("dream promote: %s", e)

    # 5) rebuild vector index
    try:
        report["vector_rebuilt"] = service.rebuild_vector_index(drama_id)
    except Exception as e:
        logger.warning("dream vector: %s", e)
        report["vector_rebuilt"] = {"error": str(e)}

    report["finished_at"] = datetime.now().isoformat()
    try:
        service.append_audit(
            action="dream",
            layer="working",
            target_id=drama_id,
            user_id=user_id,
            drama_id=drama_id,
            detail={k: report[k] for k in ("lessons_written", "skills_promoted", "reflections") if k in report},
        )
    except Exception:
        pass
    return report


def _lesson_from_episode(ep: Dict[str, Any], *, kind: str) -> str:
    task = (ep.get("task_description") or "")[:80]
    if kind == "failure":
        err = "; ".join((ep.get("errors") or [])[:3]) or (ep.get("resolution") or "")[:120]
        if not err and not task:
            return ""
        return f"失败复盘[{task}]: {err}"[:300]
    approach = (ep.get("approach") or "")[:120]
    decisions = "; ".join((ep.get("key_decisions") or [])[:3])
    body = decisions or approach
    if not body:
        return ""
    return f"成功路径[{task}]: {body}"[:300]


def _refresh_memory_index(service: Any, drama_id: str) -> bool:
    """把 MEMORY.md 压成短索引：阶段 + 活跃悬念 + 下一轮。"""
    current = service.get_drama_resident(drama_id) or ""
    facts = service.list_facts(drama_id, active_only=True)
    open_threads = [
        f for f in facts if f.get("predicate") in ("open_thread", "cliffhanger", "must_confirm", "forbidden")
    ][:8]
    lessons = [f for f in facts if f.get("predicate") == "lesson_learned"][:5]

    # 保留用户手写的「作品阶段」段（若有）
    stage = "连载"
    for line in current.splitlines():
        if "策划" in line or "大纲" in line or "连载" in line or "评估" in line:
            if line.strip().startswith("（"):
                continue
            stage = line.strip().lstrip("#- ").strip() or stage
            break

    lines = [
        "# MEMORY — Agent 常驻笔记",
        "",
        "> 由 dreaming 离线整理；细节在 episodes/ 与 semantic.json，勿把全文塞进此处。",
        "",
        "## 作品阶段",
        stage,
        "",
        "## 当前不变量 / 悬念",
    ]
    if open_threads:
        for f in open_threads:
            lines.append(f"- [{f.get('predicate')}] {f.get('entity_id')}: {str(f.get('value'))[:100]}")
    else:
        lines.append("- （暂无）")

    lines.extend(["", "## 已知坑 / 教训"])
    if lessons:
        for f in lessons:
            lines.append(f"- {str(f.get('value'))[:120]}")
    else:
        lines.append("- （暂无）")

    eps = service.list_episodes(drama_id, limit=5)
    lines.extend(["", "## 下一轮接着做"])
    if eps:
        last = eps[0]
        lines.append(
            f"- 续写参考最近任务: {(last.get('task_description') or '')[:80]} "
            f"→ {(last.get('resolution') or last.get('approach') or '')[:60]}"
        )
    else:
        lines.append("- （待用户指定）")

    new_content = "\n".join(lines) + "\n"
    if new_content.strip() == current.strip():
        return False
    service.set_drama_resident(drama_id, new_content, skip_injection_scan=False)
    return True


def _auto_promote(service: Any, drama_id: str, *, min_success: int) -> List[Dict[str, Any]]:
    eps = service.list_episodes(drama_id, limit=200, outcome="success")
    tag_counter: Counter = Counter()
    for e in eps:
        for t in e.get("tags") or []:
            if t and len(str(t)) >= 2:
                tag_counter[str(t).strip().lower()] += 1
    promoted: List[Dict[str, Any]] = []
    existing = {s.get("trigger", "").lower() for s in service.list_promoted_skills(drama_id)}
    for tag, cnt in tag_counter.most_common(5):
        if cnt < min_success:
            continue
        if tag in existing:
            continue
        skill = service.promote_skill_from_episodes(
            drama_id,
            name=f"路径:{tag}",
            trigger=tag,
            min_success=min_success,
        )
        if skill:
            promoted.append(skill)
    return promoted


def run_org_dream(service: Any) -> Dict[str, Any]:
    """组织级 dreaming：跨作品教训聚合为 org 级 shared_lesson。"""
    started = datetime.now().isoformat()
    report: Dict[str, Any] = {
        "started_at": started,
        "lessons_collected": 0,
        "shared_lessons_written": 0,
    }
    try:
        root = service.store.root
        lessons: List[Dict[str, Any]] = []
        projects_dir = root / "projects"
        if projects_dir.exists():
            import json as _json

            for semantic_path in projects_dir.glob("*/memory/semantic.json"):
                try:
                    data = _json.loads(semantic_path.read_text(encoding="utf-8"))
                    for f in data.get("facts") or []:
                        if f.get("predicate") == "lesson_learned" and f.get("status") == "active":
                            lessons.append(f)
                except Exception:
                    continue
        report["lessons_collected"] = len(lessons)
        # 去重后取前 N 条写入 org shared_lesson
        seen = set()
        for f in lessons[:10]:
            value = str(f.get("value") or "")[:200]
            if not value or value in seen:
                continue
            seen.add(value)
            try:
                service.upsert_org_fact(
                    entity_type="decision",
                    entity_id=f.get("drama_id") or "cross-drama",
                    predicate="shared_lesson",
                    value=value,
                    confidence="inference",
                    provenance={"source": "org_dreaming", "drama_id": f.get("drama_id")},
                )
                report["shared_lessons_written"] += 1
            except Exception:
                continue
    except Exception as e:
        logger.warning("org dream: %s", e)
    report["finished_at"] = datetime.now().isoformat()
    return report
