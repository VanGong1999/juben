"""
情节点戏剧功能分析API路由
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import asyncio
from datetime import datetime

from utils.logger import JubenLogger
from utils.agent_dispatch import build_agent_generator
from utils.agent_runtime import load_agent

router = APIRouter(prefix="/drama-analysis", tags=["情节点戏剧功能分析"])
logger = JubenLogger("drama_analysis_api")


class DramaAnalysisRequest(BaseModel):
    """情节点戏剧功能分析请求"""
    text: str
    user_id: str
    session_id: str
    chunk_size: Optional[int] = 10000
    max_length: Optional[int] = 50000


class TextTruncatorRequest(BaseModel):
    """文本截断请求"""
    text: str
    max_length: int
    user_id: str
    session_id: str


class TextSplitterRequest(BaseModel):
    """文本分割请求"""
    text: str
    chunk_size: int
    user_id: str
    session_id: str


class ResultIntegratorRequest(BaseModel):
    """结果整合请求"""
    results: List[str]
    user_id: str
    session_id: str


@router.post("/workflow")
async def drama_analysis_workflow(request: DramaAnalysisRequest):
    """
    情节点戏剧功能分析工作流
    
    完整的分析流程：
    1. 文本截断处理
    2. 文本分割处理  
    3. 并行情节点分析
    4. 结果整合
    """
    try:
        agent = load_agent("drama_workflow")
        
        request_data = {
            "text": request.text,
            "user_id": request.user_id,
            "session_id": request.session_id
        }
        
        # 执行工作流
        events = []
        async for event in build_agent_generator(agent, request_data, None):
            events.append({
                "type": event["type"],
                "data": event["data"],
                "timestamp": event["timestamp"]
            })
        
        return {
            "success": True,
            "message": "情节点戏剧功能分析工作流完成",
            "events": events
        }
        
    except Exception as e:
        logger.error(f"❌ 情节点戏剧功能分析工作流失败: {e}")
        raise HTTPException(status_code=500, detail=f"工作流执行失败: {str(e)}")


@router.post("/analyze")
async def drama_analysis(request: DramaAnalysisRequest):
    """
    单个文本的情节点分析
    """
    try:
        agent = load_agent("drama_analysis")
        
        request_data = {
            "text": request.text,
            "user_id": request.user_id,
            "session_id": request.session_id
        }
        
        # 执行分析
        events = []
        async for event in build_agent_generator(agent, request_data, None):
            events.append({
                "type": event["type"],
                "data": event["data"],
                "timestamp": event["timestamp"]
            })
        
        return {
            "success": True,
            "message": "情节点分析完成",
            "events": events
        }
        
    except Exception as e:
        logger.error(f"❌ 情节点分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.post("/text-truncator")
async def text_truncator(request: TextTruncatorRequest):
    """
    文本截断工具
    """
    try:
        agent = load_agent("text_truncator")
        
        request_data = {
            "text": request.text,
            "max_length": request.max_length,
            "user_id": request.user_id,
            "session_id": request.session_id
        }
        
        # 执行处理
        events = []
        async for event in build_agent_generator(agent, request_data, None):
            events.append({
                "type": event["type"],
                "data": event["data"],
                "timestamp": event["timestamp"]
            })
        
        return {
            "success": True,
            "message": "文本截断完成",
            "events": events
        }
        
    except Exception as e:
        logger.error(f"❌ 文本截断失败: {e}")
        raise HTTPException(status_code=500, detail=f"文本截断失败: {str(e)}")


@router.post("/text-splitter")
async def text_splitter(request: TextSplitterRequest):
    """
    文本分割工具
    """
    try:
        agent = load_agent("text_splitter")
        
        request_data = {
            "text": request.text,
            "chunk_size": request.chunk_size,
            "user_id": request.user_id,
            "session_id": request.session_id
        }
        
        # 执行处理
        events = []
        async for event in build_agent_generator(agent, request_data, None):
            events.append({
                "type": event["type"],
                "data": event["data"],
                "timestamp": event["timestamp"]
            })
        
        return {
            "success": True,
            "message": "文本分割完成",
            "events": events
        }
        
    except Exception as e:
        logger.error(f"❌ 文本分割失败: {e}")
        raise HTTPException(status_code=500, detail=f"文本分割失败: {str(e)}")


@router.post("/result-integrator")
async def result_integrator(request: ResultIntegratorRequest):
    """
    结果整合工具
    """
    try:
        agent = load_agent("result_integrator")
        
        request_data = {
            "results": request.results,
            "user_id": request.user_id,
            "session_id": request.session_id
        }
        
        # 执行整合
        events = []
        async for event in build_agent_generator(agent, request_data, None):
            events.append({
                "type": event["type"],
                "data": event["data"],
                "timestamp": event["timestamp"]
            })
        
        return {
            "success": True,
            "message": "结果整合完成",
            "events": events
        }
        
    except Exception as e:
        logger.error(f"❌ 结果整合失败: {e}")
        raise HTTPException(status_code=500, detail=f"结果整合失败: {str(e)}")


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "drama-analysis-api",
        "timestamp": datetime.now().isoformat()
    }
