"""
Agent 相关 API 路由
处理 Agent 列表、信息查询等
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from pydantic import BaseModel

from utils.logger import get_logger
from .schemas import AgentInfo, AgentListResponse

logger = get_logger("AgentAPI")


def _agent_info_from_config(cfg: Dict[str, Any]) -> AgentInfo:
    """将 config.agents 条目映射为 schemas.AgentInfo。"""
    examples: List[str] = []
    if cfg.get("input_example"):
        examples.append(cfg["input_example"])
    if cfg.get("output_example"):
        examples.append(cfg["output_example"])
    return AgentInfo(
        name=cfg.get("display_name") or cfg.get("name", ""),
        type=cfg.get("id", ""),
        description=cfg.get("description", ""),
        category=cfg.get("category", ""),
        features=cfg.get("features", []),
        status=cfg.get("status", "active"),
        capabilities=cfg.get("capabilities", []),
        examples=examples,
        product_line=cfg.get("product_line"),
    )


# 创建路由器
router = APIRouter(prefix="/agents", tags=["Agents"])


class AgentFilterParams(BaseModel):
    """Agent 过滤参数"""
    category: str = None
    capability: str = None
    search: str = None


@router.get("/list")
async def list_agents(
    category: str = None,
    capability: str = None,
    search: str = None
):
    """
    获取可用的 Agent 列表

    Args:
        category: 按类别筛选
        capability: 按能力筛选
        search: 搜索关键词

    Returns:
        Agent 列表响应
    """
    try:
        # 这里可以从配置文件或数据库获取 Agent 列表
        # 简化实现：返回硬编码的列表
        from config.agents import get_all_agents_config

        agents = get_all_agents_config()

        # 应用过滤
        if category:
            agents = [a for a in agents if a.get("category") == category]
        if capability:
            agents = [a for a in agents if capability in a.get("capabilities", [])]
        if search:
            search_lower = search.lower()
            agents = [
                a for a in agents
                if search_lower in a.get("name", "").lower() or
                   search_lower in a.get("description", "").lower()
            ]

        agent_models = [_agent_info_from_config(a) for a in agents]
        return AgentListResponse(
            success=True,
            message="获取 Agent 列表成功",
            agents=agent_models,
            total=len(agent_models),
        )

    except Exception as e:
        logger.error(f"获取 Agent 列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取 Agent 列表失败")


@router.get("/{agent_id}")
async def get_agent_info(agent_id: str):
    """
    获取特定 Agent 的详细信息

    Args:
        agent_id: Agent ID

    Returns:
        Agent 信息
    """
    try:
        from config.agents import get_agent_config

        agent = get_agent_config(agent_id)

        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} 不存在")

        detail = _agent_info_from_config(agent)
        return {
            "success": True,
            "agent": detail,
            "id": agent.get("id"),
            "api_endpoint": agent.get("api_endpoint"),
            "icon": agent.get("icon"),
            "color": agent.get("color"),
            "parameters": agent.get("parameters", {}),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取 Agent 信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取 Agent 信息失败")


@router.get("/categories")
async def list_categories():
    """
    获取 Agent 类别列表

    Returns:
        类别列表
    """
    try:
        categories = [
            {"id": "planning", "name": "策划类", "description": "短剧策划和规划"},
            {"id": "creation", "name": "创作类", "description": "剧本和内容创作"},
            {"id": "evaluation", "name": "评估类", "description": "质量评估和分析"},
            {"id": "analysis", "name": "分析类", "description": "剧情和角色分析"},
            {"id": "workflow", "name": "工作流类", "description": "多步骤创作流程"},
            {"id": "tools", "name": "工具类", "description": "辅助工具"},
        ]

        return {
            "success": True,
            "categories": categories
        }

    except Exception as e:
        logger.error(f"获取类别列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取类别列表失败")


# 导出
__all__ = ["router"]
