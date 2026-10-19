"""
Agent Memory 五层类型 — 对齐 CoALA / 5-Layer Playbook + 短剧业务

Layers:
  1. RULES      — 工作宪法（平台/作品硬约束）
  2. RESIDENT   — 常驻画像（USER.md / MEMORY.md，短硬高密度）
  3. EPISODIC   — 情节记忆（发生过什么）
  4. SEMANTIC   — 语义事实（什么为真，带证据链）
  5. PROCEDURAL — 程序技能（怎么做）
  + FORGETTING — 过期 / 取代 / 矛盾治理
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


# 记忆 schema 版本 — 用于幂等迁移（v1: 裸 facts；v2: 双时态 + 强度 + head_version）
SCHEMA_VERSION = 2


class MemoryLayer(str, Enum):
    RULES = "rules"
    RESIDENT = "resident"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    WORKING = "working"


class FactStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"
    FLAGGED = "flagged"  # 矛盾待审


class Confidence(str, Enum):
    FACT = "fact"          # 可追溯证据
    INFERENCE = "inference"
    PREFERENCE = "preference"
    HYPOTHESIS = "hypothesis"


class EpisodeOutcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


def _now() -> str:
    return datetime.now().isoformat()


def new_id(prefix: str = "mem") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@dataclass
class Provenance:
    """证据链：结论从哪来"""
    source: str = ""  # session | bible | user_edit | tool | episode | skill
    source_id: Optional[str] = None
    agent_id: Optional[str] = None
    quote: Optional[str] = None
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Provenance":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class Episode:
    """情节记忆 — 一次专家任务的可审计记录"""
    episode_id: str
    user_id: str
    drama_id: Optional[str]
    session_id: Optional[str]
    agent_id: str
    task_description: str
    approach: str = ""
    outcome: str = EpisodeOutcome.PARTIAL.value
    key_decisions: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    resolution: str = ""
    user_feedback: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    tokens_used: int = 0
    duration_seconds: float = 0
    pinned: bool = False
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Episode":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class SemanticFact:
    """语义事实 — 带本体类型、置信度、证据与治理元数据"""
    fact_id: str
    entity_type: str
    entity_id: str
    predicate: str
    value: Any
    confidence: str = Confidence.FACT.value
    status: str = FactStatus.ACTIVE.value
    scope: str = "drama"  # user | drama | agent | org
    drama_id: Optional[str] = None
    user_id: Optional[str] = None
    provenance: Optional[Dict[str, Any]] = None
    expires_at: Optional[str] = None
    superseded_by: Optional[str] = None
    pinned: bool = False
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    # 双时态 + 强度（v2）：valid_from/valid_until 保留历史，strength 做衰减召回
    valid_from: str = field(default_factory=_now)
    valid_until: Optional[str] = None
    access_count: int = 0
    last_access: Optional[str] = None
    strength: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SemanticFact":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class SkillRecord:
    """程序记忆 — 可复用创作方法（可晋升自情节）"""
    skill_id: str
    name: str
    trigger: str
    steps: List[str] = field(default_factory=list)
    tools_required: List[str] = field(default_factory=list)
    preconditions: List[str] = field(default_factory=list)
    success_criteria: str = ""
    failure_modes: List[str] = field(default_factory=list)
    version: int = 1
    success_count: int = 0
    failure_count: int = 0
    success_rate: float = 0.0
    last_used: Optional[str] = None
    source_skill_file: Optional[str] = None  # skills/*.md
    source_episode_ids: List[str] = field(default_factory=list)
    drama_id: Optional[str] = None
    enabled: bool = True
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SkillRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class Reflection:
    """反思 — 总结过去为什么成功或失败（非二手瞎总结：绑 episode）"""
    reflection_id: str
    drama_id: str
    user_id: str
    episode_id: Optional[str]
    kind: str  # success | failure | partial
    summary: str
    why: List[str] = field(default_factory=list)
    next_action: str = ""
    confidence: str = Confidence.INFERENCE.value
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Reflection":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class WorkingMemoryBundle:
    """工作记忆注入包 — 受 token 预算约束"""
    rules: str = ""
    resident: str = ""
    episodic_hits: List[Dict[str, Any]] = field(default_factory=list)
    semantic_hits: List[Dict[str, Any]] = field(default_factory=list)
    procedural: str = ""
    bible: str = ""
    total_chars: int = 0
    truncated: bool = False

    def to_prompt_block(self) -> str:
        parts: List[str] = []
        if self.rules.strip():
            parts.append("## 规则记忆（必须遵守）\n" + self.rules.strip())
        if self.resident.strip():
            parts.append("## 常驻画像 / 不变量\n" + self.resident.strip())
        if self.bible.strip():
            parts.append("## Bible / 作品设定\n" + self.bible.strip())
        if self.semantic_hits:
            lines = ["## 语义事实（当前为真）"]
            for f in self.semantic_hits:
                lines.append(
                    f"- [{f.get('entity_type')}:{f.get('entity_id')}] "
                    f"{f.get('predicate')} = {f.get('value')} "
                    f"({f.get('confidence', 'fact')})"
                )
            parts.append("\n".join(lines))
        if self.episodic_hits:
            lines = ["## 相关历史（情节记忆）"]
            for ep in self.episodic_hits:
                lines.append(
                    f"- [{ep.get('outcome')}] {ep.get('task_description', '')[:120]} "
                    f"→ {ep.get('resolution', '')[:100] or ep.get('approach', '')[:100]}"
                )
            parts.append("\n".join(lines))
        if self.procedural.strip():
            parts.append("## 程序技能（可复用方法）\n" + self.procedural.strip())
        return "\n\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rules": self.rules,
            "resident": self.resident,
            "bible": self.bible,
            "episodic_hits": self.episodic_hits,
            "semantic_hits": self.semantic_hits,
            "procedural": self.procedural,
            "total_chars": self.total_chars,
            "truncated": self.truncated,
            "prompt_block": self.to_prompt_block(),
        }
