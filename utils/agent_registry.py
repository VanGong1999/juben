"""
Agent 注册表（运行时薄封装）

元数据单一来源：config/agents.py（AGENTS_CONFIG）——这里不再硬编码重复的 class/module 清单；
运行时加载单一来源：utils/agent_runtime.load_agent。

只保留：
  1. 少数尚未纳入 config/agents.py 的老体系 agent（_LEGACY_AGENTS，仅补描述/分类）；
  2. 老体系用到的分类展示映射（category_mapping，向后兼容）；
  3. 用户自定义注册（register_agent）。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from utils.agent_runtime import (
    clear_agent_cache as _clear_runtime_cache,
    is_agent_loaded,
    load_agent,
    normalize_agent_id,
    resolve_agent_runtime,
)

logger = logging.getLogger(__name__)

# config/agents.py 的 category -> 老体系 category（向后兼容 get_all_agents_info / statistics）
_CONFIG_TO_LEGACY_CATEGORY: Dict[str, str] = {
    "orchestration": "orchestration",
    "utility": "tool",
    "planning": "creation",
    "creation": "creation",
    "evaluation": "evaluation",
    "analysis": "story_analysis",
    "workflow": "creation",
    "character": "character",
    "story": "plot",
    "tools": "tool",
}

# 老体系独有、尚未进入 config/agents.py 目录的 agent（module/class 由 resolve_agent_runtime 推导）
_LEGACY_AGENTS: Dict[str, Dict[str, str]] = {
    "juben_orchestrator": {"description": "剧本编排器 - 核心协调Agent", "category": "orchestration"},
    "juben_concierge": {"description": "剧本礼宾服务 - 意图识别与分发", "category": "orchestration"},
    "series_analysis_orchestrator": {"description": "剧集分析编排器", "category": "orchestration"},
    "series_info": {"description": "剧集信息Agent", "category": "series"},
    "series_name_extractor": {"description": "剧集名称提取Agent", "category": "series"},
    "file_reference": {"description": "文件引用解析Agent", "category": "tool"},
    "ocr": {"description": "OCR识别Agent", "category": "tool"},
    "document_generator": {"description": "文档生成Agent", "category": "tool"},
    "output_formatter": {"description": "输出格式化Agent", "category": "tool"},
    "text_splitter": {"description": "文本分割Agent", "category": "tool"},
    "text_truncator": {"description": "文本截断Agent", "category": "tool"},
    "logic_consistency": {"description": "逻辑一致性检查Agent", "category": "advanced"},
    "graph_rag": {"description": "图RAG检索Agent", "category": "advanced"},
    "meta_optimizer": {"description": "元优化器Agent", "category": "advanced"},
}


def _build_agent_configs() -> Dict[str, Dict[str, Any]]:
    configs: Dict[str, Dict[str, Any]] = {}
    try:
        from config.agents import AGENTS_CONFIG
    except Exception as e:  # pragma: no cover - 目录加载失败则回退老清单
        logger.warning("加载 config.agents 失败: %s", e)
        AGENTS_CONFIG = {}

    for aid, cfg in AGENTS_CONFIG.items():
        if aid == "auto":
            continue  # auto 是 juben_conductor 别名，避免重复
        configs[aid] = {
            "description": cfg.get("description") or "",
            "category": _CONFIG_TO_LEGACY_CATEGORY.get(cfg.get("category"), "uncategorized"),
            "enabled": cfg.get("status") != "disabled",
        }

    for aid, extra in _LEGACY_AGENTS.items():
        configs[aid] = {
            "description": extra.get("description") or "",
            "category": extra.get("category") or "uncategorized",
            "enabled": True,
        }
    return configs


class AgentRegistry:
    """Agent 注册表（元数据派生 + 运行时统一加载）。"""

    def __init__(self):
        self.agent_configs = _build_agent_configs()
        # 用户自定义注册的 agent：agent_type -> class
        self._custom_classes: Dict[str, Any] = {}

        # 分类展示映射（向后兼容 enhanced API）
        self.category_mapping = {
            "orchestration": {"name": "核心编排", "description": "系统核心协调和分发Agent", "icon": "🎯"},
            "story_analysis": {"name": "故事分析", "description": "故事内容和质量分析", "icon": "📖"},
            "character": {"name": "角色开发", "description": "角色创建和关系分析", "icon": "👤"},
            "plot": {"name": "情节开发", "description": "情节规划和工作流", "icon": "🎬"},
            "creation": {"name": "短剧创作", "description": "短剧策划和创作", "icon": "✍️"},
            "evaluation": {"name": "评估分析", "description": "各类评估和分析Agent", "icon": "📊"},
            "series": {"name": "剧集分析", "description": "剧集内容分析", "icon": "📺"},
            "tool": {"name": "工具", "description": "辅助工具Agent", "icon": "🔧"},
            "advanced": {"name": "高级功能", "description": "高级分析和优化Agent", "icon": "🚀"},
        }

    # ------------------------------------------------------------------
    # 解析
    # ------------------------------------------------------------------
    def _resolve_agent_type(self, agent_type: str) -> Optional[str]:
        aid = normalize_agent_id(agent_type or "")
        if not aid:
            return None
        if aid in self.agent_configs or aid in self._custom_classes:
            return aid
        return None

    # ------------------------------------------------------------------
    # 加载
    # ------------------------------------------------------------------
    async def get_agent(self, agent_type: str) -> Optional[Any]:
        """获取 Agent 实例（统一走 utils.agent_runtime.load_agent）。"""
        aid = normalize_agent_id(agent_type or "")
        if not aid:
            return None
        # 用户自定义注册优先
        if aid in self._custom_classes:
            try:
                return self._custom_classes[aid]()
            except Exception as e:
                logger.error("创建自定义 Agent 失败: %s (%s)", aid, e)
                return None
        try:
            return load_agent(aid)
        except Exception as e:
            logger.error("创建 Agent 失败: %s (%s)", aid, e)
            return None

    # ------------------------------------------------------------------
    # 元数据
    # ------------------------------------------------------------------
    def get_available_agents(self, category: Optional[str] = None) -> List[str]:
        if category:
            return [
                aid for aid, cfg in self.agent_configs.items()
                if cfg.get("category") == category and cfg.get("enabled", True)
            ]
        return [
            aid for aid, cfg in self.agent_configs.items()
            if cfg.get("enabled", True)
        ]

    def get_agent_info(self, agent_type: str) -> Optional[Dict[str, Any]]:
        resolved = self._resolve_agent_type(agent_type)
        if resolved is None:
            return None

        cfg = self.agent_configs.get(resolved) or {}
        class_name = ""
        module_path = ""
        try:
            module_path, class_name = resolve_agent_runtime(resolved)
        except Exception:
            pass

        category = cfg.get("category", "")
        return {
            "agent_type": resolved,
            "class_name": class_name,
            "module_path": module_path,
            "description": cfg.get("description", ""),
            "category": category,
            "enabled": cfg.get("enabled", True),
            "is_loaded": is_agent_loaded(resolved),
            "category_info": self.category_mapping.get(category, {}),
        }

    def get_all_agents_info(self) -> Dict[str, Dict[str, Any]]:
        result: Dict[str, Dict[str, Any]] = {}
        for aid, cfg in self.agent_configs.items():
            if not cfg.get("enabled", True):
                continue
            category = cfg.get("category", "uncategorized")
            result.setdefault(
                category,
                {
                    "category_info": self.category_mapping.get(
                        category, {"name": category, "icon": "📦"}
                    ),
                    "agents": [],
                },
            )
            result[category]["agents"].append(self.get_agent_info(aid))
        return result

    def get_agents_by_category(self) -> Dict[str, Dict[str, Any]]:
        return self.get_all_agents_info()

    def get_categories(self) -> Dict[str, Dict[str, Any]]:
        return dict(self.category_mapping)

    def get_agent_statistics(self) -> Dict[str, Any]:
        enabled = {aid for aid, c in self.agent_configs.items() if c.get("enabled", True)}
        loaded = {aid for aid in enabled if is_agent_loaded(aid)}

        category_stats: Dict[str, int] = {}
        for aid in enabled:
            cat = self.agent_configs[aid].get("category", "uncategorized")
            category_stats[cat] = category_stats.get(cat, 0) + 1

        return {
            "total_agents": len(self.agent_configs),
            "enabled_agents": len(enabled),
            "loaded_agents": len(loaded),
            "load_rate": len(loaded) / len(enabled) if enabled else 0,
            "category_stats": category_stats,
            "categories": list(self.category_mapping.keys()),
            "available_agents": sorted(enabled),
        }

    # ------------------------------------------------------------------
    # 维护
    # ------------------------------------------------------------------
    def register_agent(
        self,
        agent_type: str,
        agent_class,
        module_path: str = "",
        description: str = "",
        category: str = "custom",
        enabled: bool = True,
    ) -> None:
        aid = normalize_agent_id(agent_type or "") or agent_type
        self._custom_classes[aid] = agent_class
        self.agent_configs[aid] = {
            "description": description,
            "category": category,
            "enabled": enabled,
        }

    def clear_agent_cache(self, agent_type: Optional[str] = None) -> None:
        _clear_runtime_cache(agent_type)
        if agent_type:
            self._custom_classes.pop(normalize_agent_id(agent_type), None)
        else:
            self._custom_classes.clear()
