"""
短剧创作本体 — Snowflake 式 ontology 约束写入与查询
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

# 实体类型
ENTITY_TYPES: Set[str] = {
    "user",
    "drama",
    "character",
    "episode",
    "plot_thread",
    "world_rule",
    "platform",
    "style",
    "decision",
    "skill",
}

# 谓词 / 关系
PREDICATES: Dict[str, Dict[str, Any]] = {
    # 用户偏好
    "prefers_genre": {"target": "string", "scope": "user", "expires_days": 180},
    "avoids_trope": {"target": "string", "scope": "user", "expires_days": 180},
    "language_style": {"target": "string", "scope": "user", "expires_days": 365},
    # 人物
    "has_trait": {"target": "string", "scope": "drama", "expires_days": None},
    "relationship": {"target": "string", "scope": "drama", "expires_days": None},
    "arc_status": {"target": "string", "scope": "drama", "expires_days": 90},
    "voice_note": {"target": "string", "scope": "drama", "expires_days": 180},
    # 情节
    "open_thread": {"target": "string", "scope": "drama", "expires_days": 60},
    "resolved_thread": {"target": "string", "scope": "drama", "expires_days": None},
    "cliffhanger": {"target": "string", "scope": "drama", "expires_days": 30},
    "beat_committed": {"target": "string", "scope": "drama", "expires_days": None},
    # 世界 / 平台
    "world_invariant": {"target": "string", "scope": "drama", "expires_days": None},
    "platform_rule": {"target": "string", "scope": "drama", "expires_days": None},
    "word_count_target": {"target": "string", "scope": "drama", "expires_days": None},
    # 决策 / 治理
    "must_confirm": {"target": "string", "scope": "drama", "expires_days": None},
    "forbidden": {"target": "string", "scope": "drama", "expires_days": None},
    "lesson_learned": {"target": "string", "scope": "drama", "expires_days": 120},
    # 风格示例（用户级语义事实，替代旧 StyleMemory 向量持久化）
    "style_example": {"target": "string", "scope": "user", "expires_days": 365},
    # Org 级共享（跨智能体共同维护）
    "org_rule": {"target": "string", "scope": "org", "expires_days": None},
    "best_practice": {"target": "string", "scope": "org", "expires_days": 180},
    "shared_lesson": {"target": "string", "scope": "org", "expires_days": 120},
}

# 强度衰减的 S（半衰期系数，天）：越大衰减越慢。由 predicate 重要度决定。
# 重要/长期 -> 大 S；短暂/悬念 -> 小 S。
PREDICATE_STRENGTH_S: Dict[str, float] = {
    "world_invariant": 365.0,
    "platform_rule": 365.0,
    "forbidden": 365.0,
    "must_confirm": 180.0,
    "has_trait": 120.0,
    "relationship": 120.0,
    "org_rule": 365.0,
    "best_practice": 120.0,
    "style_example": 180.0,
    "lesson_learned": 90.0,
    "shared_lesson": 90.0,
    "open_thread": 30.0,
    "cliffhanger": 14.0,
    "arc_status": 60.0,
    "voice_note": 90.0,
    "resolved_thread": 30.0,
    "beat_committed": 30.0,
    "prefers_genre": 180.0,
    "avoids_trope": 180.0,
    "language_style": 365.0,
    "word_count_target": 30.0,
}

DEFAULT_STRENGTH_S = 60.0
STRENGTH_FLOOR = 0.05


def validate_fact(
    entity_type: str,
    predicate: str,
    value: Any,
    *,
    entity_id: str = "",
) -> Optional[str]:
    """返回错误信息；None 表示通过。"""
    if entity_type not in ENTITY_TYPES:
        return f"未知实体类型: {entity_type}"
    if predicate not in PREDICATES:
        return f"未知谓词: {predicate}"
    if value is None or (isinstance(value, str) and not value.strip()):
        return "value 不能为空"
    if not entity_id:
        return "entity_id 必填"
    return None


def expires_days_for(predicate: str) -> Optional[int]:
    meta = PREDICATES.get(predicate) or {}
    return meta.get("expires_days")


def default_scope_for(predicate: str) -> str:
    meta = PREDICATES.get(predicate) or {}
    return meta.get("scope") or "drama"


def strength_s_for(predicate: str) -> float:
    """返回该谓词的强度衰减系数 S（天）。"""
    return PREDICATE_STRENGTH_S.get(predicate, DEFAULT_STRENGTH_S)


def ontology_schema() -> Dict[str, Any]:
    return {
        "entity_types": sorted(ENTITY_TYPES),
        "predicates": PREDICATES,
        "domain": "short_drama_creation",
        "notes": "规则进 RULES.md；偏好进 USER/MEMORY；过程进 episodes；可复用方法进 skills",
    }
