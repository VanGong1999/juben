"""
聊天相关 API 路由
处理用户聊天请求、流式响应等
"""
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.stream_manager import get_stream_response_generator
from utils.logger import get_logger
from utils.error_handler import handle_error
from utils.agent_dispatch import build_agent_generator
from apis.dramas.ownership import auth_uid
from .schemas import ChatRequest, StreamEvent

logger = get_logger("ChatAPI")

# 创建路由器
router = APIRouter(prefix="/chat", tags=["聊天"])


@router.post("")
async def chat_handler(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    http_request: Request
):
    """
    处理聊天请求 - 支持流式输出

    Args:
        request: 聊天请求
        background_tasks: 后台任务
        http_request: HTTP 请求对象

    Returns:
        StreamingResponse: 流式响应
    """
    try:
        # 记录请求
        logger.info(f"收到聊天请求: user_id={request.user_id}, session_id={request.session_id}")
        logger.debug(f"请求内容: {request.input[:100] if len(request.input) > 100 else request.input}...")

        # 解析引用（@file / @drama[episode:N] / @note…）
        resolved_input = request.input
        reference_trace = []
        needs_ref_resolve = (
            (request.file_ids and request.file_refs == "auto")
            or ("@drama[" in (request.input or ""))
            or ("@file[" in (request.input or ""))
            or ("@note[" in (request.input or ""))
        )
        if needs_ref_resolve:
            try:
                from utils.reference_resolver import get_juben_reference_resolver

                resolver = get_juben_reference_resolver()
                resolved_input = await resolver.resolve_references(
                    request.input,
                    request.user_id or "default_user",
                    request.session_id or "default",
                    query=request.input or "",
                    project_id=request.project_id,
                )
                reference_trace = resolver.get_reference_trace()
                logger.debug(f"解析引用完成: 引用数量 {len(reference_trace)}")
            except Exception:
                logger.warning("引用解析失败，使用原文", exc_info=True)
                resolved_input = request.input

        # 构建请求数据
        request_data = {
            "input": resolved_input,
            "query": resolved_input,
            "user_id": request.user_id,
            "session_id": request.session_id,
            "file_ids": request.file_ids or [],
            "auto_mode": request.auto_mode,
            "user_selections": request.user_selections or [],
            "reference_trace": reference_trace,
            "original_input": request.input,
            "stream_mode": True,
            "model_provider": request.model_provider,
            "model": request.model,
            "api_key": request.api_key,
            "base_url": request.base_url,
        }

        # 解析本轮 Agent：空/auto → Conductor；尊重 session handoff
        from utils.agent_infra.handoffs import resolve_turn_agent

        session_id_for_route = request.session_id or f"session_{hash(request.input)}"

        # 保存用户消息到会话存储（用于「历史对话」列表与切换）
        try:
            from utils.storage_manager import get_storage, ChatMessage as StorageChatMessage

            storage = get_storage()
            await storage.save_chat_message(
                StorageChatMessage(
                    user_id=auth_uid(http_request) or request.user_id or "default_user",
                    session_id=session_id_for_route,
                    message_type="user",
                    content=request.input or "",
                )
            )
        except Exception:
            logger.warning("保存用户消息失败", exc_info=True)

        resolved = resolve_turn_agent(
            agent_id=request.agent_id,
            session_id=session_id_for_route,
        )
        agent_id = resolved["agent_id"]
        request_data["resolved_agent_id"] = agent_id
        request_data["agent_route_source"] = resolved.get("source")
        logger.info(
            f"路由 Agent: requested={request.agent_id} resolved={agent_id} source={resolved.get('source')}"
        )

        try:
            # 统一运行时加载（单一事实源 utils.agent_runtime.load_agent）
            from utils.agent_runtime import load_agent

            agent = load_agent(agent_id, fresh=True)
        except Exception as agent_error:
            logger.error(f"Agent加载失败: agent_id={agent_id}, error={agent_error}")
            raise HTTPException(status_code=404, detail=f"未找到可用Agent: {agent_id}")

        # 用户自备 Key / Base URL / 模型覆盖
        if hasattr(agent, "apply_llm_overrides"):
            try:
                agent.apply_llm_overrides(
                    provider=request.model_provider,
                    model=request.model,
                    api_key=request.api_key,
                    base_url=request.base_url,
                )
            except Exception as override_err:
                logger.warning(f"应用 LLM 覆盖失败，将使用默认客户端: {override_err}")

        # 构建上下文并获取 Agent 生成器
        context = {
            "user_id": request.user_id,
            "session_id": session_id_for_route,
            "project_id": request.project_id,
            "drama_id": request.project_id,
            "request_path": str(http_request.url.path),
            "model_provider": request.model_provider,
            "model": request.model,
            "api_key": request.api_key,
            "base_url": request.base_url,
            "resolved_agent_id": agent_id,
            "agent_route_source": resolved.get("source"),
        }

        async def _orchestrated_generator():
            # 首包告知前端当前负责 Agent
            yield {
                "event_type": "agent_decision",
                "agent_source": agent_id,
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "agent_id": agent_id,
                    "source": resolved.get("source"),
                    "requested": request.agent_id,
                },
                "metadata": {
                    "active_agent": agent_id,
                    "route_source": resolved.get("source"),
                },
            }
            collected: list[str] = []
            async for ev in build_agent_generator(agent, request_data, context):
                et = ev.get("event_type") or ev.get("type") or ""
                data = ev.get("data")
                if et in ("llm_chunk", "final_result", "content") and isinstance(data, str):
                    collected.append(data)
                yield ev

            # 流结束后保存助手最终回复到会话存储
            assistant_content = "".join(collected).strip()
            if assistant_content:
                try:
                    from utils.storage_manager import get_storage, ChatMessage as StorageChatMessage

                    await get_storage().save_chat_message(
                        StorageChatMessage(
                            user_id=request.user_id or "default_user",
                            session_id=session_id_for_route,
                            message_type="assistant",
                            content=assistant_content,
                            agent_name=agent_id,
                        )
                    )
                except Exception:
                    logger.warning("保存助手消息失败", exc_info=True)

        agent_generator = _orchestrated_generator()

        # 创建流式响应（统一转换为标准 SSE 事件）
        session_id = session_id_for_route
        user_id = request.user_id or "default_user"
        stream_generator = get_stream_response_generator()
        return StreamingResponse(
            stream_generator.generate(
                agent_generator=agent_generator,
                session_id=session_id,
                user_id=user_id
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"聊天处理失败: {str(e)}")
        error_result = await handle_error(e, "chat_processing", {
            "user_id": getattr(request, 'user_id', 'unknown'),
            "session_id": getattr(request, 'session_id', 'unknown')
        })
        raise HTTPException(status_code=500, detail=error_result.get("message", "处理失败"))


@router.post("/resume")
async def resume_chat(request: Request):
    """
    恢复中断的聊天会话

    Args:
        request: HTTP 请求对象

    Returns:
        StreamingResponse: 从断点继续的流式响应
    """
    try:
        # 从请求体获取恢复参数
        request_data = await request.json()
        session_id = request_data.get("session_id")
        message_id = request_data.get("message_id")
        from_sequence = request_data.get("from_sequence", 0)

        if not session_id or not message_id:
            raise HTTPException(status_code=400, detail="缺少必要参数")

        logger.info(f"恢复会话: session_id={session_id}, message_id={message_id}, from_sequence={from_sequence}")

        # 获取流式会话管理器
        from utils.stream_manager import get_stream_session_manager
        session_manager = get_stream_session_manager()

        # 恢复会话（重放 Redis 缓存的 SSE 事件）
        stream_generator = await session_manager.resume_session(session_id, message_id, from_sequence)

        if not stream_generator:
            raise HTTPException(status_code=404, detail="会话不存在或已过期")

        return StreamingResponse(
            stream_generator,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"恢复会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail="恢复会话失败")


@router.post("/stop")
async def stop_chat(request: Request):
    """
    停止正在进行的聊天会话

    Args:
        request: HTTP 请求对象

    Returns:
        停止结果
    """
    try:
        request_data = await request.json()
        session_id = request_data.get("session_id")
        message_id = request_data.get("message_id")

        if not session_id:
            raise HTTPException(status_code=400, detail="缺少 session_id")

        logger.info(f"停止会话: session_id={session_id}, message_id={message_id}")

        # 获取流式会话管理器
        from utils.stream_manager import get_stream_session_manager
        session_manager = get_stream_session_manager()

        stopped = await session_manager.stop_session(session_id, message_id)

        return {
            "success": stopped,
            "message": "会话已停止" if stopped else "会话不存在或已结束"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"停止会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail="停止会话失败")


@router.get("/sessions")
async def list_sessions(user_id: str, request: Request = None):
    """
    获取用户的聊天会话列表

    Args:
        user_id: 用户 ID（认证用户存在时以 JWT 注入的 user_id 为准）
    """
    try:
        from utils.storage_manager import get_storage
        storage = get_storage()

        uid = auth_uid(request) if request else None
        sessions = await storage.list_user_sessions(uid or user_id)

        return {
            "success": True,
            "sessions": sessions
        }

    except Exception as e:
        logger.error(f"获取会话列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取会话列表失败")


@router.get("/sessions/{session_id}")
async def get_session_history(session_id: str, request: Request = None):
    """
    获取会话的历史消息（认证用户存在时强制归属校验）
    """
    try:
        from utils.storage_manager import get_storage
        storage = get_storage()

        uid = auth_uid(request) if request else None
        history = await storage.get_session_history(session_id, user_id=uid)

        return {
            "success": True,
            "history": history
        }

    except Exception as e:
        logger.error(f"获取会话历史失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取会话历史失败")


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, request: Request = None):
    """
    删除会话（认证用户存在时强制归属校验）
    """
    try:
        from utils.storage_manager import get_storage
        storage = get_storage()

        uid = auth_uid(request) if request else None
        await storage.delete_session(session_id, user_id=uid)

        return {
            "success": True,
            "message": "会话已删除"
        }

    except Exception as e:
        logger.error(f"删除会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除会话失败")


# 导出
__all__ = ["router"]
