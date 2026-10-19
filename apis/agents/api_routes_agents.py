"""
Agents 管理相关的 API 路由
提供 Agent 列表、详情、分类等功能
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging

from utils.llm_client import (
    ZhipuModel,
    ModelType,
    list_available_models,
    get_model_for_purpose,
)
from utils.logger import get_logger
from config.agents import AGENTS_CONFIG, get_all_agents_config, get_agent_config

logger = get_logger("AgentsAPI")

router = APIRouter(prefix="/juben/agents", tags=["Agents管理"])


class AgentInfo(BaseModel):
    """Agent 基础信息"""
    model_config = {"extra": "ignore"}

    id: str
    name: str
    display_name: str
    description: str
    category: str
    icon: str
    model: str
    api_endpoint: str
    status: str
    features: List[str] = []
    capabilities: List[str] = []
    input_example: str = ""
    output_example: str = ""
    product_line: Optional[str] = None


class AgentDetail(AgentInfo):
    """Agent 详细信息"""
    pass


class AgentListResponse(BaseModel):
    """Agent 列表响应"""
    success: bool
    agents: List[AgentInfo]
    total: int
    categories: Dict[str, List[AgentInfo]]


@router.get("/list", response_model=AgentListResponse)
async def list_agents(
    category: Optional[str] = None,
    status: Optional[str] = None
) -> AgentListResponse:
    """
    获取所有可用的 Agents 列表

    Args:
        category: 按分类筛选 (planning/creation/evaluation/analysis/workflow/character/story/utility)
        status: 按状态筛选 (active/beta/experimental)

    Returns:
        AgentListResponse: Agent 列表
    """
    try:
        agents = []

        for config in get_all_agents_config():
            # 筛选条件
            if category and config.get("category") != category:
                continue
            if status and config.get("status") != status:
                continue

            agents.append(AgentInfo(**config))

        # 按分类组织
        categories = {}
        for agent in agents:
            cat = agent.category
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(agent)

        logger.info(f"返回 {len(agents)} 个 Agents")

        return AgentListResponse(
            success=True,
            agents=agents,
            total=len(agents),
            categories=categories
        )
    except Exception as e:
        logger.error(f"获取 Agent 列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
async def get_agent_categories() -> Dict[str, Any]:
    """
    获取所有 Agent 分类

    Returns:
        Dict: 分类列表和每个分类的数量
    """
    try:
        categories = {
            "planning": {"name": "策划类", "icon": "📋", "description": "剧本策划和规划相关"},
            "creation": {"name": "创作类", "icon": "✍️", "description": "内容创作和生成"},
            "evaluation": {"name": "评估类", "icon": "📊", "description": "质量评估和分析"},
            "analysis": {"name": "分析类", "icon": "🔍", "description": "深度分析和洞察"},
            "workflow": {"name": "工作流", "icon": "🔄", "description": "多步骤工作流程"},
            "character": {"name": "人物类", "icon": "👤", "description": "人物相关功能"},
            "story": {"name": "故事类", "icon": "📖", "description": "故事处理功能"},
            "utility": {"name": "工具类", "icon": "🛠️", "description": "辅助工具功能"},
            "orchestration": {"name": "编排类", "icon": "🧭", "description": "总控编排与组合调用"},
            "tools": {"name": "Infra", "icon": "⚙️", "description": "Agent Infra 模板与工具环"},
        }

        # 统计每个分类的 Agent 数量
        category_counts = {}
        for config in AGENTS_CONFIG.values():
            cat = config.get("category", "utility")
            category_counts[cat] = category_counts.get(cat, 0) + 1

        return {
            "success": True,
            "categories": categories,
            "counts": category_counts,
            "total": len(AGENTS_CONFIG)
        }
    except Exception as e:
        logger.error(f"获取分类失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_agents(
    query: str,
    category: Optional[str] = None
) -> Dict[str, Any]:
    """
    搜索 Agents

    Args:
        query: 搜索关键词
        category: 分类筛选

    Returns:
        Dict: 搜索结果
    """
    try:
        query_lower = query.lower()
        results = []

        for config in get_all_agents_config():
            # 筛选分类
            if category and config.get("category") != category:
                continue

            # 搜索匹配
            searchable_text = (
                config.get("name", "") + " " +
                config.get("display_name", "") + " " +
                config.get("description", "") + " " +
                " ".join(config.get("features", []))
            ).lower()

            if query_lower in searchable_text:
                results.append(AgentInfo(**config))

        return {
            "success": True,
            "query": query,
            "results": results,
            "total": len(results)
        }
    except Exception as e:
        logger.error(f"搜索 Agents 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}", response_model=AgentDetail)
async def get_agent_detail(agent_id: str) -> AgentDetail:
    """
    获取指定 Agent 的详细信息

    Args:
        agent_id: Agent ID

    Returns:
        AgentDetail: Agent 详细信息
    """
    try:
        config = get_agent_config(agent_id)
        if config is None:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} 不存在")

        return AgentDetail(**config)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取 Agent 详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
