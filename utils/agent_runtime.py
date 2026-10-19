"""
Agent 运行时加载与命名归一化 — 全项目唯一入口。

此前「一个 agent 怎么加载、叫什么名字」散落在三处，反复抄写且互相不一致：
  - utils/agent_infra/subagents.py  AGENT_ID_ALIASES / normalize_agent_id
  - utils/agent_naming.py          AGENT_ALIASES / canonical_agent_id
  - utils/agent_registry.py        alias_mapping + 硬编码 agent_configs
  - utils/atelier_pipeline.py      _AGENT_IMPORT / _snake_to_pascal / load_agent

本模块收敛为单一事实源：
  - normalize_agent_id：把旧名 / 短别名 / `_agent` 后缀统一到 config/agents.py 的规范 id
  - resolve_agent_runtime：规范 id -> (module_path, class_name)
  - load_agent：加载 Agent 实例（带缓存）

规范 id 以 config/agents.py 的 AGENTS_CONFIG 为准（如 short_drama_planner，不带 `_agent` 后缀）。
"""

from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path
from typing import Any, Dict, Tuple

# ---------------------------------------------------------------------------
# 命名归一化
# ---------------------------------------------------------------------------

# 短别名 / 旧名 -> 规范 id（合并原 subagents.AGENT_ID_ALIASES + agent_registry.alias_mapping 里的短别名）
AGENT_ID_ALIASES: Dict[str, str] = {
    "creator": "short_drama_creator",
    "planner": "short_drama_planner",
    "evaluation": "short_drama_evaluation",
    "conductor": "juben_conductor",
    "auto": "juben_conductor",
    "episode_batch": "episode_batch_creator",
    "batch_creator": "episode_batch_creator",
    "episode_writer_agent": "episode_writer",
    "serialize": "episode_batch_creator",
    "video_prompt": "video_prompt_writer",
    "seedance": "video_prompt_batch",
    "doubao_video": "video_prompt_batch",
    "video_batch": "video_prompt_batch",
    "story_summary": "story_summary_generator",
    "story_analysis": "story_evaluation",
    "memory": "memory_curator",
    "memory_curator_agent": "memory_curator",
    "character_profile": "character_profile_generator",
    "character_relationship": "character_relationship_analyzer",
    "plot_points": "major_plot_points",
    "plot_workflow": "plot_points_workflow",
    "mindmap": "mind_map",
    "web_search": "websearch",
    "file_ref": "file_reference",
    "series": "series_analysis",
    "series_info": "series_info",
    "drama_evaluation": "drama_analysis",
}


def normalize_agent_id(agent_id: str) -> str:
    """归一化 agent id 到 config/agents.py 的规范形式（去掉 `_agent` 后缀 + 别名）。"""
    raw = (agent_id or "").strip().lower()
    if not raw:
        return raw
    # 旧体系常用 `short_drama_planner_agent` 这类后缀；统一剥掉
    if raw.endswith("_agent"):
        raw = raw[: -len("_agent")]
    return AGENT_ID_ALIASES.get(raw, raw)


def snake_to_pascal(name: str) -> str:
    return "".join(p.capitalize() for p in name.split("_") if p)


# ---------------------------------------------------------------------------
# 运行时解析
# ---------------------------------------------------------------------------

# 直接按文件加载（spec_from_file_location），避开 agents/__init__ 的循环导入。
# 值：(文件名, 类名)
_STANDALONE: Dict[str, Tuple[str, str]] = {
    "minimal_tool_agent": ("minimal_tool_agent.py", "MinimalToolAgent"),
    "juben_conductor": ("juben_conductor.py", "JubenConductor"),
    "memory_curator": ("memory_curator_agent.py", "MemoryCuratorAgent"),
}

# 不满足「agents.{id}_agent + {PascalCase(id)}Agent」默认规则的例外
# 值：(module_path, class_name)
_EXPLICIT: Dict[str, Tuple[str, str]] = {
    # 类名是 WebSearchAgent（S 大写），默认规则会生成 WebsearchAgent
    "websearch": ("agents.websearch_agent", "WebSearchAgent"),
    # 缩写类名（默认规则会把 IP/OCR/RAG 首字母小写化）
    "ip_evaluation": ("agents.ip_evaluation_agent", "IPEvaluationAgent"),
    "ocr": ("agents.ocr_agent", "OCRAgent"),
    "graph_rag": ("agents.graph_rag_agent", "GraphRAGAgent"),
    # 模块名不带 `_agent` 后缀的编排类
    "juben_orchestrator": ("agents.juben_orchestrator", "JubenOrchestrator"),
    "juben_concierge": ("agents.juben_concierge", "JubenConcierge"),
    "series_analysis_orchestrator": ("agents.series_analysis_orchestrator", "SeriesAnalysisOrchestrator"),
}


def resolve_agent_runtime(agent_id: str) -> Tuple[str, str]:
    """返回 (module_path, class_name)；standalone 用文件名表示 module_path。"""
    aid = normalize_agent_id(agent_id)
    if aid in _STANDALONE:
        return _STANDALONE[aid]
    if aid in _EXPLICIT:
        return _EXPLICIT[aid]
    return (f"agents.{aid}_agent", f"{snake_to_pascal(aid)}Agent")


_agent_cache: Dict[str, Any] = {}


def load_agent(agent_id: str, *, fresh: bool = False) -> Any:
    """统一加载 Agent 实例（全项目唯一入口）。"""
    aid = normalize_agent_id(agent_id)
    if not fresh and aid in _agent_cache:
        return _agent_cache[aid]

    module_path, class_name = resolve_agent_runtime(aid)
    if aid in _STANDALONE:
        # module_path 实际是文件名，直接按文件加载
        path = Path(__file__).resolve().parent.parent / "agents" / module_path
        spec = importlib.util.spec_from_file_location(f"{aid}_standalone", path)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        instance = getattr(module, class_name)()
    else:
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        instance = cls()

    if not fresh:
        _agent_cache[aid] = instance
    return instance


def is_agent_loaded(agent_id: str) -> bool:
    return normalize_agent_id(agent_id) in _agent_cache


def clear_agent_cache(agent_id: str = None) -> None:
    global _agent_cache
    if agent_id:
        _agent_cache.pop(normalize_agent_id(agent_id), None)
    else:
        _agent_cache.clear()


__all__ = [
    "AGENT_ID_ALIASES",
    "normalize_agent_id",
    "snake_to_pascal",
    "resolve_agent_runtime",
    "load_agent",
    "is_agent_loaded",
    "clear_agent_cache",
]
