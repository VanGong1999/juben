"""
生产级 Agent Memory（五层）

参考:
- Agent Memory — The 5-Layer Playbook (Working/Episodic/Semantic/Procedural/Forgetting)
- WquGuru: 规则文件 · 常驻画像 · 历史召回 · 证据治理 · 反思与技能沉淀

短剧业务映射:
  RULES.md      → 平台/作品硬约束
  USER.md       → 创作者偏好（题材/桥段/文风）
  MEMORY.md     → 作品不变量与下一轮续写点
  episodes/     → 专家任务过程（成功/失败/卡点）
  semantic.json → 人物/悬念/世界事实（本体校验）
  skills        → 全局 skills/*.md + 作品晋升技能
"""

from .types import (
    SCHEMA_VERSION,
    MemoryLayer,
    Episode,
    SemanticFact,
    SkillRecord,
    Reflection,
    WorkingMemoryBundle,
    EpisodeOutcome,
    Confidence,
    FactStatus,
    new_id,
)
from .ontology import ontology_schema, validate_fact
from .store import MemoryStore
from .service import AgentMemoryService, get_agent_memory_service
from .version_store import MemoryVersionStore, unified_diff
from .vector_index import MemoryVectorIndex, embed_text
from .dreaming import run_dream, run_org_dream
from .governance import scan_injection, evidence_ref

__all__ = [
    "SCHEMA_VERSION",
    "MemoryLayer",
    "Episode",
    "SemanticFact",
    "SkillRecord",
    "Reflection",
    "WorkingMemoryBundle",
    "EpisodeOutcome",
    "Confidence",
    "FactStatus",
    "new_id",
    "ontology_schema",
    "validate_fact",
    "MemoryStore",
    "AgentMemoryService",
    "get_agent_memory_service",
    "MemoryVersionStore",
    "unified_diff",
    "MemoryVectorIndex",
    "embed_text",
    "run_dream",
    "run_org_dream",
    "scan_injection",
    "evidence_ref",
]
