"""
小说初筛评估和分析智能体的API路由
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, ConfigDict, Field
from typing import Dict, Any, Optional, List
import asyncio
import json
from datetime import datetime

from agents.novel_screening_evaluation_agent import NovelScreeningEvaluationAgent
from utils.agent_dispatch import build_agent_generator


# 创建路由器
router = APIRouter(prefix="/api/novel-screening", tags=["小说初筛评估"])


# 请求模型
class NovelScreeningRequest(BaseModel):
    """小说初筛评估请求模型"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "file": "这是一个关于现代都市爱情的故事...",
            "chunk_size": 10000,
            "length_size": 800,
            "theme": "都市爱情"
        }
    })

    file: Optional[str] = Field(None, description="完整小说文件内容")
    short_file: Optional[str] = Field(None, description="短篇小说文件内容")
    chunk_size: int = Field(10000, description="文本分割块大小", ge=1000, le=50000)
    length_size: int = Field(800, description="文本截断长度", ge=100, le=2000)
    theme: str = Field("小说", description="故事题材类型")


class NovelScreeningResponse(BaseModel):
    """小说初筛评估响应模型"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "message": "小说初筛评估完成",
            "data": {
                "rating": "A",
                "document_url": "https://example.com/document/123",
                "analysis": "评估分析结果...",
                "workflow": "full_file_branch"
            },
            "timestamp": "2024-01-01T00:00:00"
        }
    })

    success: bool = Field(description="请求是否成功")
    message: str = Field(description="响应消息")
    data: Optional[Dict[str, Any]] = Field(None, description="响应数据")
    timestamp: str = Field(description="响应时间戳")


class NovelScreeningStreamResponse(BaseModel):
    """小说初筛评估流式响应模型"""
    event_type: str = Field(description="事件类型")
    data: Dict[str, Any] = Field(description="事件数据")
    timestamp: str = Field(description="时间戳")


# 全局智能体实例
_novel_screening_agent = None


def get_novel_screening_agent() -> NovelScreeningEvaluationAgent:
    """获取小说初筛评估智能体实例"""
    global _novel_screening_agent
    if _novel_screening_agent is None:
        _novel_screening_agent = NovelScreeningEvaluationAgent()
    return _novel_screening_agent


@router.post("/evaluate", response_model=NovelScreeningResponse)
async def evaluate_novel_screening(request: NovelScreeningRequest):
    """
    小说初筛评估接口
    
    根据coze工作流设计，支持两种处理分支：
    1. 完整文件分支：截断→分割→大纲总结→评估→评分分析
    2. 短文件分支：截断→评估→评分分析
    """
    try:
        # 验证输入
        if not request.file and not request.short_file:
            raise HTTPException(
                status_code=400,
                detail="必须提供file或short_file参数"
            )
        
        # 获取智能体实例
        agent = get_novel_screening_agent()
        
        # 构建请求数据
        request_data = {
            "file": request.file or "",
            "short_file": request.short_file or "",
            "chunk_size": request.chunk_size,
            "length_size": request.length_size,
            "theme": request.theme
        }
        
        # 处理请求并收集结果
        final_result = None
        evaluation_data = {
            "workflow": None,
            "rating": None,
            "document_url": None,
            "analysis": None,
            "statistics": {}
        }
        
        async for event in build_agent_generator(agent, request_data, None):
            event_type = event.get("event_type")
            data = event.get("data", {})
            
            if event_type == "final_result":
                final_result = data
                evaluation_data.update({
                    "workflow": data.get("workflow"),
                    "rating": data.get("rating"),
                    "document_url": data.get("document_url"),
                    "analysis": data.get("analysis")
                })
            elif event_type == "workflow_complete":
                evaluation_data["rating"] = data.get("final_rating")
            elif event_type == "error":
                raise HTTPException(
                    status_code=500,
                    detail=f"评估过程中发生错误: {data.get('error')}"
                )
        
        # 构建响应
        response = NovelScreeningResponse(
            success=True,
            message="小说初筛评估完成",
            data=evaluation_data,
            timestamp=datetime.now().isoformat()
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"服务器内部错误: {str(e)}"
        )


@router.post("/evaluate/stream")
async def evaluate_novel_screening_stream(request: NovelScreeningRequest):
    """
    小说初筛评估流式接口
    
    提供实时的评估进度和结果
    """
    try:
        # 验证输入
        if not request.file and not request.short_file:
            raise HTTPException(
                status_code=400,
                detail="必须提供file或short_file参数"
            )
        
        # 获取智能体实例
        agent = get_novel_screening_agent()
        
        # 构建请求数据
        request_data = {
            "file": request.file or "",
            "short_file": request.short_file or "",
            "chunk_size": request.chunk_size,
            "length_size": request.length_size,
            "theme": request.theme
        }
        
        # 流式处理请求
        async def generate_events():
            try:
                async for event in build_agent_generator(agent, request_data, None):
                    yield {
                        "event_type": event.get("event_type"),
                        "data": event.get("data", {}),
                        "timestamp": datetime.now().isoformat()
                    }
            except Exception as e:
                yield {
                    "event_type": "error",
                    "data": {
                        "error": str(e),
                        "message": "流式处理过程中发生错误"
                    },
                    "timestamp": datetime.now().isoformat()
                }
        
        return generate_events()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"服务器内部错误: {str(e)}"
        )


@router.get("/agent/info")
async def get_agent_info():
    """获取智能体信息"""
    try:
        agent = get_novel_screening_agent()
        info = agent.get_workflow_info()
        
        return {
            "success": True,
            "message": "获取智能体信息成功",
            "data": info,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取智能体信息失败: {str(e)}"
        )


@router.get("/tools")
async def get_available_tools():
    """获取可用的工具智能体列表"""
    try:
        agent = get_novel_screening_agent()
        tools_info = {}
        
        for tool_name, description in agent.available_tools.items():
            try:
                tool_agent = await agent._get_tool_agent(tool_name)
                if tool_agent and hasattr(tool_agent, 'get_tool_info'):
                    tools_info[tool_name] = tool_agent.get_tool_info()
                else:
                    tools_info[tool_name] = {
                        "tool_name": tool_name,
                        "description": description,
                        "status": "not_available"
                    }
            except Exception as e:
                tools_info[tool_name] = {
                    "tool_name": tool_name,
                    "description": description,
                    "status": "error",
                    "error": str(e)
                }
        
        return {
            "success": True,
            "message": "获取工具列表成功",
            "data": {
                "tools": tools_info,
                "total_count": len(tools_info)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取工具列表失败: {str(e)}"
        )


@router.post("/test")
async def test_agent_as_tool():
    """测试Agent as Tool机制"""
    try:
        agent = get_novel_screening_agent()
        test_results = {}
        
        # 测试各个工具智能体
        test_cases = [
            {
                "tool_name": "text_truncator",
                "input": {"text": "测试文本" * 100, "max_length": 100}
            },
            {
                "tool_name": "story_summary",
                "input": {"text": "从前有一个小王子..."}
            },
            {
                "tool_name": "story_evaluation",
                "input": {"story_text": "一个关于友情的故事", "theme": "青春", "round": 1}
            },
            {
                "tool_name": "score_analyzer",
                "input": {"evaluation_results": ["评估结果1", "评估结果2"]}
            }
        ]
        
        for test_case in test_cases:
            try:
                result = await agent._call_agent_as_tool(
                    test_case["tool_name"],
                    test_case["input"]
                )
                test_results[test_case["tool_name"]] = {
                    "status": "success",
                    "result": result
                }
            except Exception as e:
                test_results[test_case["tool_name"]] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return {
            "success": True,
            "message": "Agent as Tool测试完成",
            "data": {
                "test_results": test_results,
                "passed_count": len([r for r in test_results.values() if r["status"] == "success"]),
                "total_count": len(test_results)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"测试失败: {str(e)}"
        )


# 健康检查接口
@router.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "success": True,
        "message": "小说初筛评估智能体运行正常",
        "data": {
            "agent_status": "running",
            "available_tools": len(get_novel_screening_agent().available_tools),
            "workflow_state": get_novel_screening_agent().workflow_state
        },
        "timestamp": datetime.now().isoformat()
    }
