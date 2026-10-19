"""
工具调用 API 路由
提供工具列表、工具执行、工具历史等功能
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import logging
import asyncio
from datetime import datetime

from utils.tool_system import get_tool_registry, get_tool_executor
from utils.agent_tools import (
    ToolContext,
    get_agent_tool_registry,
    get_tool_harness,
    resolve_tool_name,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tools", tags=["工具调用"])


def _build_tool_context(raw: Optional[Dict[str, Any]]) -> ToolContext:
    raw = raw or {}
    # 默认不允许写；危险工具需显式 allow_write
    return ToolContext(
        user_id=str(raw.get("user_id") or "default_user"),
        drama_id=raw.get("drama_id"),
        session_id=raw.get("session_id"),
        agent_id=raw.get("agent_id"),
        workspace_root=raw.get("workspace_root"),
        allow_write=bool(raw.get("allow_write", False)),
        metadata=dict(raw.get("metadata") or {}),
    )


# ==================== 请求模型 ====================

class ToolExecuteRequest(BaseModel):
    """工具执行请求"""
    tool_name: str = Field(..., description="工具名称")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="工具参数")
    context: Optional[Dict[str, Any]] = Field(None, description="执行上下文")
    confirm_dangerous: bool = Field(False, description="危险工具二次确认")
    role: Optional[str] = Field(None, description="调用方角色（开发调试；生产应从 JWT 注入）")


class ToolBatchExecuteRequest(BaseModel):
    """批量工具执行请求"""
    tools: List[Dict[str, Any]] = Field(..., description="工具列表，每个包含 tool_name 和 parameters")


class ComparePromptsRequest(BaseModel):
    """Prompt 对比评测请求"""
    base_prompt: str = Field(..., description="基础 Prompt")
    test_prompt: str = Field(..., description="测试 Prompt")
    input_context: Dict[str, Any] = Field(..., description="输入上下文（相同的内容）")
    target_audience: str = Field(default="大众", description="目标受众")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据（实验标签等）")


class QuickEvaluateRequest(BaseModel):
    """快速评测请求"""
    content: str = Field(..., description="待评测内容")
    evaluation_type: str = Field(default="quick", description="评测类型: quick, detailed, commercial")
    target_audience: str = Field(default="大众", description="目标受众")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


# ==================== API 端点 ====================

@router.get("/list")
async def list_tools(category: Optional[str] = None):
    """获取 Agent Tools 目录（prebuilt / external）"""
    try:
        from utils.agent_tools import ToolCategory

        registry = get_agent_tool_registry()
        cat = ToolCategory(category) if category in ("prebuilt", "external") else None
        tools = [t.ui_schema() for t in registry.list(category=cat, enabled_only=False)]
        return {
            "success": True,
            "data": tools,
            "total": len(tools),
            "categories": {"prebuilt": "Harness 预置", "external": "外部工具"},
        }
    except Exception as e:
        logger.error(f"[工具列表] 错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schemas")
async def get_tool_schemas(category: Optional[str] = None):
    """OpenAI Function Calling Schema"""
    try:
        from utils.agent_tools import ToolCategory

        registry = get_agent_tool_registry()
        cat = ToolCategory(category) if category in ("prebuilt", "external") else None
        schemas = registry.openai_tools(category=cat)
        return {
            "success": True,
            "data": schemas,
            "format": "openai_function_calling",
            "total": len(schemas),
        }
    except Exception as e:
        logger.error(f"[工具Schema] 错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute")
async def execute_tool(request: ToolExecuteRequest):
    """执行工具：优先 Agent Tools，未命中回退旧 tool_system；危险工具需 ACL。"""
    try:
        name = resolve_tool_name(request.tool_name)
        harness = get_tool_harness()
        tool = harness.registry.get(name)
        ctx = _build_tool_context(request.context)

        if tool:
            from utils.agent_infra.tool_acl import check_tool_access

            user = {"role": request.role or (request.context or {}).get("role") or "user"}
            decision = check_tool_access(
                tool_name=name,
                dangerous=bool(tool.dangerous),
                user=user,
                allow_write=bool(ctx.allow_write),
                confirm_dangerous=bool(request.confirm_dangerous),
            )
            if not decision.allowed:
                status = 403
                raise HTTPException(
                    status_code=status,
                    detail={
                        "message": decision.reason,
                        "require_confirm": decision.require_confirm,
                        "tool": name,
                    },
                )

            packed = await harness.execute(
                name,
                request.parameters,
                ctx=ctx,
            )
            return {
                "success": packed["success"],
                "tool_name": packed["tool_name"],
                "tool_call_id": packed["tool_call_id"],
                "result": {
                    "log_id": packed["tool_call_id"],
                    "msg": "success" if packed["success"] else (packed.get("error") or "error"),
                    "code": 0 if packed["success"] else -1,
                    "data": packed["result"],
                    "llm_text": packed.get("llm_text"),
                },
                "error": packed.get("error"),
            }

        executor = get_tool_executor()
        return await executor.execute(
            tool_name=request.tool_name,
            parameters=request.parameters,
            context=request.context,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[工具执行] 错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch_execute")
async def batch_execute_tools(request: ToolBatchExecuteRequest):
    """批量执行工具"""
    try:
        results = []
        for tool_request in request.tools:
            sub = ToolExecuteRequest(
                tool_name=tool_request.get("tool_name"),
                parameters=tool_request.get("parameters") or {},
                context=tool_request.get("context"),
            )
            results.append(await execute_tool(sub))
        return {"success": True, "data": results, "total": len(results)}
    except Exception as e:
        logger.error(f"[批量工具执行] 错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_execution_history(limit: int = 50):
    """工具执行历史"""
    try:
        history = get_tool_harness().get_history(limit=limit)
        return {
            "success": True,
            "data": list(reversed(history)),
            "total": len(history),
        }
    except Exception as e:
        logger.error(f"[工具历史] 错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{tool_name}/schema")
async def get_tool_schema(tool_name: str):
    """单个工具 Schema"""
    try:
        name = resolve_tool_name(tool_name)
        tool = get_agent_tool_registry().get(name)
        if tool:
            return {"success": True, "data": tool.ui_schema()}

        legacy = get_tool_registry().get(tool_name)
        if not legacy:
            raise HTTPException(status_code=404, detail=f"工具不存在: {tool_name}")
        return {"success": True, "data": legacy.get_schema()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[工具Schema] 错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 便捷端点 ====================

@router.post("/search")
async def quick_search(query: str, max_results: int = 10):
    """快速搜索 — 走 web_search 工具"""
    try:
        result = await execute_tool(
            ToolExecuteRequest(
                tool_name="web_search",
                parameters={"query": query, "top_k": max_results},
            )
        )
        if result.get("success"):
            data = (result.get("result") or {}).get("data") or {}
            details = data.get("details") if isinstance(data, dict) else {}
            refs = (details or {}).get("raw", {}).get("references") if isinstance(details, dict) else []
            return {
                "success": True,
                "query": query,
                "results": refs or data,
                "total": len(refs) if isinstance(refs, list) else 0,
                "llm_text": (result.get("result") or {}).get("llm_text"),
            }
        return {"success": False, "error": result.get("error", "执行失败")}
    except Exception as e:
        logger.error(f"[快速搜索] 错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/baike")
async def quick_baike(query: str, include_videos: bool = False):
    """
    快速百科查询 - 便捷端点

    直接执行百科工具的简化接口
    """
    try:
        executor = get_tool_executor()
        result = await executor.execute(
            tool_name="baike_search",
            parameters={"query": query, "include_videos": include_videos}
        )

        if result["success"]:
            data = result["result"]["data"]
            return {
                "success": True,
                "query": query,
                "baike": data.get("baike"),
                "videos": data.get("videos", [])
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "执行失败")
            }
    except Exception as e:
        logger.error(f"[快速百科] 错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 健康检查 ====================

@router.get("/health")
async def health_check():
    """工具系统健康检查"""
    try:
        registry = get_agent_tool_registry()
        tools = [t.name for t in registry.list(enabled_only=False)]
        return {
            "status": "ok",
            "tools_registered": len(tools),
            "tools": tools,
            "harness": "agent_tools",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ==================== 评测对比 ====================

@router.post("/evaluate")
async def quick_evaluate(request: QuickEvaluateRequest):
    """
    快速评测内容

    对剧本内容进行多维度评分（逻辑、角色、爆点、对白、节奏、情感、创意、商业）
    """
    try:
        from agents.short_drama_evaluation_agent import get_evaluation_agent

        agent = get_evaluation_agent()

        result = await agent.evaluate_content(
            content=request.content,
            evaluation_type=request.evaluation_type,
            target_audience=request.target_audience,
            metadata=request.metadata or {}
        )

        return {
            "success": True,
            "data": {
                "overall_score": result.overall_score,
                "scores": result.scores,
                "reasons": result.reasons,
                "overall_reason": result.overall_reason,
                "suggestions": result.suggestions,
                "strengths": result.strengths,
                "weaknesses": result.weaknesses,
                "commercial_potential": result.commercial_potential,
                "target_audience_match": result.target_audience_match
            },
            "evaluated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"[快速评测] 错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare_prompts")
async def compare_prompts(request: ComparePromptsRequest):
    """
    Prompt 对比评测

    使用相同的 input_context，分别用 base_prompt 和 test_prompt 生成内容，
    然后对两个生成结果进行背靠背评测对比
    """
    try:
        from agents.short_drama_creator_agent import short_drama_creator_agent
        from agents.short_drama_evaluation_agent import get_evaluation_agent

        user_id = "system"
        session_id = f"compare_{datetime.utcnow().timestamp()}"

        logger.info(f"[Prompt对比] 开始对比评测, session_id={session_id}")

        # 并发生成两个版本的内容
        logger.info(f"[Prompt对比] 并发生成版本 A (base_prompt) 和 B (test_prompt)")

        result_a, result_b = await asyncio.gather(
            short_drama_creator_agent.process_request(
                request_data={
                    "prompt_template": request.base_prompt,
                    **request.input_context
                },
                context={"user_id": user_id, "session_id": f"{session_id}_a"}
            ),
            short_drama_creator_agent.process_request(
                request_data={
                    "prompt_template": request.test_prompt,
                    **request.input_context
                },
                context={"user_id": user_id, "session_id": f"{session_id}_b"}
            )
        )

        # 提取生成的内容
        content_a = result_a.get("result", "") if isinstance(result_a, dict) else str(result_a)
        content_b = result_b.get("result", "") if isinstance(result_b, dict) else str(result_b)

        logger.info(f"[Prompt对比] 内容生成完成, 开始评测对比")

        # 使用评测 Agent 进行对比评测
        agent = get_evaluation_agent()

        comparison_result = await agent.evaluate_comparison(
            content_a=content_a,
            content_b=content_b,
            target_audience=request.target_audience
        )

        # 组装完整返回结果
        response_data = {
            "comparison": {
                "winner": comparison_result.winner,
                "score_delta": comparison_result.score_delta,
                "overall_delta": comparison_result.overall_delta,
                "comparison_summary": comparison_result.comparison_summary,
                "recommendation": comparison_result.recommendation
            },
            "version_a": {
                "prompt": request.base_prompt,
                "result": comparison_result.version_a
            },
            "version_b": {
                "prompt": request.test_prompt,
                "result": comparison_result.version_b
            },
            "metadata": request.metadata or {},
            "compared_at": datetime.utcnow().isoformat()
        }

        logger.info(f"[Prompt对比] 对比评测完成, winner={comparison_result.winner}, delta={comparison_result.overall_delta:.2f}")

        return {
            "success": True,
            "data": response_data
        }

    except Exception as e:
        logger.error(f"[Prompt对比] 错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare_contents")
async def compare_contents(
    content_a: str,
    content_b: str,
    target_audience: str = "大众",
    metadata: Optional[Dict[str, Any]] = None
):
    """
    内容对比评测

    对两段已生成的内容进行背靠背评测对比
    """
    try:
        from agents.short_drama_evaluation_agent import get_evaluation_agent

        agent = get_evaluation_agent()

        comparison_result = await agent.evaluate_comparison(
            content_a=content_a,
            content_b=content_b,
            target_audience=target_audience
        )

        return {
            "success": True,
            "data": {
                "comparison": {
                    "winner": comparison_result.winner,
                    "score_delta": comparison_result.score_delta,
                    "overall_delta": comparison_result.overall_delta,
                    "comparison_summary": comparison_result.comparison_summary,
                    "recommendation": comparison_result.recommendation
                },
                "version_a": comparison_result.version_a,
                "version_b": comparison_result.version_b,
                "metadata": metadata or {},
                "compared_at": datetime.utcnow().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"[内容对比] 错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evaluation_history")
async def get_evaluation_history(limit: int = 20):
    """
    获取评测历史记录

    返回最近的评测/对比记录
    """
    try:
        from agents.short_drama_evaluation_agent import get_evaluation_agent

        agent = get_evaluation_agent()
        history = await agent.get_evaluation_history(limit=limit)

        return {
            "success": True,
            "data": history,
            "total": len(history)
        }
    except Exception as e:
        logger.error(f"[评测历史] 错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))
