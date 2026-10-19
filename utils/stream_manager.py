"""
流式响应管理器
提供稳定的 SSE 流式传输、Redis 暂存、断点续传功能

代码作者：宫灵瑞
创建时间：2026年2月7日

功能：
1. 流式事件缓存（Redis 暂存最后 50 个 token）
2. 断点续传支持
3. 异常处理和 SSE 错误事件
4. Message ID 生成和追踪
"""
import asyncio
import json
import logging
import uuid
import os
from typing import AsyncGenerator, Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

try:
    from .redis_client import get_redis_client
    from .logger import get_logger
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from utils.redis_client import get_redis_client
    from utils.logger import get_logger


class StreamEventType(Enum):
    """流式事件类型"""
    MESSAGE = "message"           # 消息事件（正文）
    THINKING = "thinking"         # 思考过程
    PROGRESS = "progress"         # 进度更新
    ERROR = "error"               # 错误事件
    COMPLETE = "complete"         # 完成事件
    HEARTBEAT = "heartbeat"       # 心跳事件
    AGENT_DECISION = "agent_decision"  # 路由/决策
    SUBAGENT = "subagent"         # 子专家起止
    HANDOFF = "handoff"           # 会话交接
    COMPOSITION = "composition"   # 组合编排进度
    SYSTEM = "system"             # 进度提示（不混入正文）
    BILLING = "billing"           # 计费提示
    TOOL = "tool"                 # 工具调用


@dataclass
class StreamEvent:
    """流式事件数据类"""
    event_type: StreamEventType
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    message_id: str = ""
    sequence: int = 0

    def to_sse(self) -> str:
        """转换为 SSE 格式"""
        event_data = {
            "event": self.event_type.value,
            "data": {
                "content": self.content,
                "metadata": self.metadata,
                "timestamp": self.timestamp,
                "message_id": self.message_id,
                "sequence": self.sequence
            }
        }
        return f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "event_type": self.event_type.value,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "message_id": self.message_id,
            "sequence": self.sequence
        }


class StreamSessionManager:
    """
    流式会话管理器

    负责：
    1. 生成唯一 message_id
    2. 缓存流式事件到 Redis
    3. 支持断点续传
    """

    # Redis 键前缀
    STREAM_CACHE_PREFIX = "stream:cache:"
    STREAM_META_PREFIX = "stream:meta:"

    # 配置
    MAX_CACHE_SIZE = int(os.getenv("STREAM_CACHE_SIZE", "200"))  # 默认缓存 200 个事件
    CACHE_TTL = 3600     # 缓存过期时间（秒）

    def __init__(self):
        self.logger = get_logger("StreamSessionManager")
        self._redis_client = None

    async def _get_redis(self):
        """获取 Redis 客户端"""
        if self._redis_client is None:
            self._redis_client = await get_redis_client()
        return self._redis_client

    def generate_message_id(self, session_id: str, user_id: str) -> str:
        """生成唯一消息 ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique = uuid.uuid4().hex[:8]
        return f"msg_{user_id}_{session_id}_{timestamp}_{unique}"

    async def save_event(
        self,
        message_id: str,
        event: StreamEvent
    ) -> bool:
        """
        保存事件到 Redis

        Args:
            message_id: 消息 ID
            event: 流式事件

        Returns:
            bool: 是否保存成功
        """
        try:
            redis = await self._get_redis()
            if not redis:
                return False

            # 缓存键
            cache_key = f"{self.STREAM_CACHE_PREFIX}{message_id}"

            # 事件数据
            event_data = json.dumps(event.to_dict())

            # 使用 Redis List 存储事件
            await redis.rpush(cache_key, event_data)

            # 限制缓存大小
            await redis.ltrim(cache_key, -self.MAX_CACHE_SIZE, -1)

            # 设置过期时间
            await redis.expire(cache_key, self.CACHE_TTL)

            return True

        except Exception as e:
            self.logger.error(f"保存事件失败: {e}")
            return False

    async def resume_session(
        self,
        session_id: str,
        message_id: str,
        from_sequence: int = 0,
    ):
        """
        恢复会话流（供 chat_routes /resume 调用）。
        返回 SSE async generator；无缓存时返回 None。
        """
        events = await self.get_cached_events(message_id, from_sequence)
        if not events:
            return None
        # get_stream_response_generator 在模块底部定义，运行时可用
        return get_stream_response_generator().resume(message_id, from_sequence)

    async def stop_session(self, session_id: str, message_id: Optional[str] = None) -> bool:
        """
        停止会话：标记 abort + 清理流缓存。
        """
        try:
            from utils.stop_manager import StopReason, get_juben_stop_manager

            mgr = await get_juben_stop_manager()
            # user_id 未知时用 session 占位；stop_manager 以 session 维度工作
            await mgr.request_stop(
                user_id="stream",
                session_id=session_id,
                reason=StopReason.USER_REQUEST,
            )
        except Exception as e:
            self.logger.warning(f"stop_manager 标记失败: {e}")

        # 记录 abort 标记到 Redis，供运行中的 loop 检查
        try:
            redis = await self._get_redis()
            if redis:
                abort_key = f"stream:abort:{session_id}"
                await redis.set(abort_key, message_id or "1", ex=3600)
        except Exception as e:
            self.logger.warning(f"写入 abort 标记失败: {e}")

        if message_id:
            await self.clear_cache(message_id)
        return True

    async def is_aborted(self, session_id: str) -> bool:
        try:
            redis = await self._get_redis()
            if not redis:
                return False
            return bool(await redis.exists(f"stream:abort:{session_id}"))
        except Exception:
            return False

    async def get_cached_events(
        self,
        message_id: str,
        from_sequence: int = 0
    ) -> List[StreamEvent]:
        """
        获取缓存的事件

        Args:
            message_id: 消息 ID
            from_sequence: 从哪个序列号开始获取

        Returns:
            List[StreamEvent]: 事件列表
        """
        try:
            redis = await self._get_redis()
            if not redis:
                return []

            cache_key = f"{self.STREAM_CACHE_PREFIX}{message_id}"

            # 获取所有缓存事件
            cached_data = await redis.lrange(cache_key, 0, -1)

            events = []
            for data in cached_data:
                try:
                    event_dict = json.loads(data)
                    event = StreamEvent(
                        event_type=StreamEventType(event_dict["event_type"]),
                        content=event_dict["content"],
                        metadata=event_dict.get("metadata", {}),
                        timestamp=event_dict.get("timestamp", ""),
                        message_id=event_dict.get("message_id", ""),
                        sequence=event_dict.get("sequence", 0)
                    )
                    # 只返回序列号大于 from_sequence 的事件
                    if event.sequence > from_sequence:
                        events.append(event)
                except Exception as e:
                    self.logger.warning(f"解析缓存事件失败: {e}")

            return events

        except Exception as e:
            self.logger.error(f"获取缓存事件失败: {e}")
            return []

    async def clear_cache(self, message_id: str) -> bool:
        """
        清除消息缓存

        Args:
            message_id: 消息 ID

        Returns:
            bool: 是否清除成功
        """
        try:
            redis = await self._get_redis()
            if not redis:
                return False

            cache_key = f"{self.STREAM_CACHE_PREFIX}{message_id}"
            await redis.delete(cache_key)

            return True

        except Exception as e:
            self.logger.error(f"清除缓存失败: {e}")
            return False

    async def save_message_meta(
        self,
        message_id: str,
        session_id: str,
        user_id: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        保存消息元数据

        Args:
            message_id: 消息 ID
            session_id: 会话 ID
            user_id: 用户 ID
            metadata: 元数据

        Returns:
            bool: 是否保存成功
        """
        try:
            redis = await self._get_redis()
            if not redis:
                return False

            meta_key = f"{self.STREAM_META_PREFIX}{message_id}"

            meta_data = {
                "message_id": message_id,
                "session_id": session_id,
                "user_id": user_id,
                "created_at": datetime.now().isoformat(),
                **metadata
            }

            await redis.setex(
                meta_key,
                self.CACHE_TTL * 2,  # 元数据保存更长时间
                json.dumps(meta_data)
            )

            return True

        except Exception as e:
            self.logger.error(f"保存消息元数据失败: {e}")
            return False

    async def get_message_meta(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        获取消息元数据

        Args:
            message_id: 消息 ID

        Returns:
            Optional[Dict]: 元数据
        """
        try:
            redis = await self._get_redis()
            if not redis:
                return None

            meta_key = f"{self.STREAM_META_PREFIX}{message_id}"
            data = await redis.get(meta_key)

            if data:
                return json.loads(data)

            return None

        except Exception as e:
            self.logger.error(f"获取消息元数据失败: {e}")
            return None


class StreamResponseGenerator:
    """
    流式响应生成器

    提供稳定的 SSE 流式传输，支持：
    1. 事件缓存
    2. 异常处理
    3. 心跳机制
    """

    def __init__(
        self,
        session_manager: StreamSessionManager = None,
        enable_cache: bool = True,
        heartbeat_interval: int = 30
    ):
        """
        初始化生成器

        Args:
            session_manager: 会话管理器
            enable_cache: 是否启用缓存
            heartbeat_interval: 心跳间隔（秒）
        """
        self.session_manager = session_manager or StreamSessionManager()
        self.enable_cache = enable_cache
        self.heartbeat_interval = heartbeat_interval
        self.logger = get_logger("StreamResponseGenerator")

    async def generate(
        self,
        agent_generator: AsyncGenerator[Dict[str, Any], None],
        session_id: str,
        user_id: str,
        message_id: str = None
    ) -> AsyncGenerator[str, None]:
        """
        生成流式响应

        Args:
            agent_generator: Agent 事件生成器
            session_id: 会话 ID
            user_id: 用户 ID
            message_id: 消息 ID（可选，自动生成）

        Yields:
            str: SSE 格式的事件
        """
        # 生成 message_id
        if not message_id:
            message_id = self.session_manager.generate_message_id(session_id, user_id)

        # 保存消息元数据
        await self.session_manager.save_message_meta(
            message_id, session_id, user_id,
            {"status": "started"}
        )

        sequence = 0
        last_event_time = asyncio.get_event_loop().time()

        # 创建一个队列来合并 agent 事件和心跳事件
        event_queue: asyncio.Queue = asyncio.Queue(maxsize=200)

        # Agent 事件处理任务
        async def process_agent_events():
            nonlocal sequence, last_event_time
            try:
                async for agent_event in agent_generator:
                    sequence += 1
                    last_event_time = asyncio.get_event_loop().time()

                    # 转换为 StreamEvent
                    stream_event = self._convert_agent_event(
                        agent_event,
                        message_id,
                        sequence
                    )

                    # 缓存事件
                    if self.enable_cache:
                        await self.session_manager.save_event(message_id, stream_event)

                    # 放入队列
                    await event_queue.put(("event", stream_event))

                # 发送完成信号
                await event_queue.put(("done", None))

            except Exception as e:
                self.logger.error(f"Agent 事件处理失败: {e}")
                # 发送错误事件
                error_event = StreamEvent(
                    event_type=StreamEventType.ERROR,
                    content=str(e),
                    metadata={"error_type": type(e).__name__},
                    message_id=message_id,
                    sequence=sequence + 1
                )
                await event_queue.put(("event", error_event))
                await event_queue.put(("done", None))

        # 心跳任务
        async def heartbeat_task():
            nonlocal last_event_time
            try:
                while True:
                    await asyncio.sleep(self.heartbeat_interval)

                    current_time = asyncio.get_event_loop().time()
                    time_since_last_event = current_time - last_event_time

                    # 只在没有新事件时发送心跳
                    if time_since_last_event >= self.heartbeat_interval:
                        heartbeat_event = StreamEvent(
                            event_type=StreamEventType.HEARTBEAT,
                            content="ping",
                            metadata={"last_sequence": sequence},
                            message_id=message_id,
                            sequence=sequence
                        )
                        await event_queue.put(("heartbeat", heartbeat_event))

            except asyncio.CancelledError:
                pass

        # 启动任务
        agent_task = asyncio.create_task(process_agent_events())
        heartbeat_task_obj = asyncio.create_task(heartbeat_task())

        try:
            # 处理队列中的事件
            while True:
                event_type, event = await event_queue.get()

                if event_type == "done":
                    break

                if event_type == "event":
                    try:
                        yield event.to_sse()
                    except Exception as e:
                        self.logger.error(f"SSE发送失败: {e}")
                        await self.session_manager.save_message_meta(
                            message_id, session_id, user_id,
                            {"status": "error", "error": str(e)}
                        )
                        break

                    # 检查是否是完成事件
                    if event.event_type == StreamEventType.COMPLETE:
                        # 更新元数据
                        await self.session_manager.save_message_meta(
                            message_id, session_id, user_id,
                            {"status": "completed", "total_events": sequence}
                        )
                        break

                    # 检查是否是错误事件
                    if event.event_type == StreamEventType.ERROR:
                        # 更新元数据
                        await self.session_manager.save_message_meta(
                            message_id, session_id, user_id,
                            {"status": "error", "error": event.content}
                        )
                        break

                elif event_type == "heartbeat":
                    # 心跳事件不缓存，直接发送
                    try:
                        yield event.to_sse()
                    except Exception as e:
                        self.logger.error(f"SSE心跳发送失败: {e}")
                        await self.session_manager.save_message_meta(
                            message_id, session_id, user_id,
                            {"status": "error", "error": str(e)}
                        )
                        break

        except Exception as e:
            self.logger.error(f"流式生成失败: {e}")
            error_event = StreamEvent(
                event_type=StreamEventType.ERROR,
                content=str(e),
                metadata={"error_type": type(e).__name__},
                message_id=message_id,
                sequence=sequence + 1
            )
            yield error_event.to_sse()

        finally:
            # 取消任务
            agent_task.cancel()
            heartbeat_task_obj.cancel()

            try:
                await agent_task
            except asyncio.CancelledError:
                pass

            try:
                await heartbeat_task_obj
            except asyncio.CancelledError:
                pass

    def _convert_agent_event(
        self,
        agent_event: Dict[str, Any],
        message_id: str,
        sequence: int
    ) -> StreamEvent:
        """
        转换 Agent 事件为 StreamEvent

        Args:
            agent_event: Agent 事件
            message_id: 消息 ID
            sequence: 序列号

        Returns:
            StreamEvent: 流式事件
        """
        event_type_str = agent_event.get("event_type", agent_event.get("type", "message"))
        raw_data = agent_event.get("data", agent_event.get("content", ""))

        # 映射事件类型（未列出的：data 是 str → 正文；data 是 dict/list → 元信息，不混入正文）
        event_type_map = {
            "thinking": StreamEventType.THINKING,
            "progress": StreamEventType.PROGRESS,
            "error": StreamEventType.ERROR,
            "complete": StreamEventType.COMPLETE,
            "agent_decision": StreamEventType.AGENT_DECISION,
            "subagent_start": StreamEventType.SUBAGENT,
            "subagent_end": StreamEventType.SUBAGENT,
            "handoff": StreamEventType.HANDOFF,
            "composition_progress": StreamEventType.COMPOSITION,
            # 进度/计费/工具类：不要混入正文
            "system": StreamEventType.SYSTEM,
            "billing": StreamEventType.BILLING,
            "tool_call": StreamEventType.TOOL,
            "tool_return": StreamEventType.TOOL,
            # 工具起止/处理中事件（data 是 dict 元信息，不能混入正文）
            "tool_start": StreamEventType.TOOL,
            "tool_processing": StreamEventType.TOOL,
            "tool_complete": StreamEventType.TOOL,
            "tool_result": StreamEventType.TOOL,
            "tool_error": StreamEventType.TOOL,
            # 工作流/批处理/步骤类事件（data 是 dict 元信息）
            "workflow_start": StreamEventType.SYSTEM,
            "workflow_step": StreamEventType.SYSTEM,
            "workflow_progress": StreamEventType.SYSTEM,
            "workflow_complete": StreamEventType.SYSTEM,
            "workflow_processing": StreamEventType.SYSTEM,
            "step_start": StreamEventType.SYSTEM,
            "step_complete": StreamEventType.SYSTEM,
            "batch_start": StreamEventType.SYSTEM,
            "batch_processing": StreamEventType.SYSTEM,
            "batch_complete": StreamEventType.SYSTEM,
            "processing_start": StreamEventType.SYSTEM,
            "processing_complete": StreamEventType.SYSTEM,
            "stream_complete": StreamEventType.SYSTEM,
        }

        event_type = event_type_map.get(event_type_str)
        if event_type is None:
            # 未映射：结构化数据 / 短进度文案 → system；长正文（报告）→ message
            # 人物关系分析等会 emit identifying_characters 等自定义类型，data 是「正在…」短句；
            # 若当 MESSAGE 会在前端被拼成一行。注意 analysis_complete 带 stage=complete 且正文很长，必须仍走 MESSAGE。
            meta_preview = agent_event.get("metadata") or {}
            text_preview = raw_data if isinstance(raw_data, str) else ""
            stage = str(meta_preview.get("stage") or "")
            is_finalish = stage in ("complete", "error", "done", "final") or event_type_str.endswith(
                ("_complete", "_error", "_done", "_result")
            )
            short_progress_text = bool(
                text_preview
                and len(text_preview) < 160
                and not text_preview.lstrip().startswith("#")
                and (
                    text_preview.rstrip().endswith(("...", "…"))
                    or text_preview.startswith("正在")
                    or text_preview.startswith("开始")
                )
            )
            progress_event_name = any(
                event_type_str.startswith(p)
                for p in (
                    "identifying_",
                    "analyzing_",
                    "enriching_",
                    "building_",
                    "generating_",
                    "formatting_",
                )
            ) or event_type_str in (
                "analysis_start",
                "analysis_progress",
            )
            looks_like_progress = (not is_finalish) and (
                short_progress_text
                or progress_event_name
                or (bool(stage) and short_progress_text)
            )
            event_type = (
                StreamEventType.SYSTEM
                if isinstance(raw_data, (dict, list)) or looks_like_progress
                else StreamEventType.MESSAGE
            )
        if isinstance(raw_data, (dict, list)):
            content = json.dumps(raw_data, ensure_ascii=False)
        else:
            content = raw_data if raw_data is not None else ""

        # 输出侧脱敏（API Key / secret / token → xx）；失败不阻断流式输出
        try:
            from utils.agent_infra.output_hooks import redact_agent_output

            content = redact_agent_output(content)
        except Exception as e:
            self.logger.warning(f"输出脱敏失败: {e}")

        metadata = dict(agent_event.get("metadata") or {})
        metadata.setdefault("original_event_type", event_type_str)
        if agent_event.get("agent_source"):
            metadata.setdefault("agent_source", agent_event["agent_source"])

        return StreamEvent(
            event_type=event_type,
            content=content if isinstance(content, str) else str(content),
            metadata=metadata,
            timestamp=agent_event.get("timestamp", datetime.now().isoformat()),
            message_id=message_id,
            sequence=sequence
        )

    async def resume(
        self,
        message_id: str,
        from_sequence: int = 0
    ) -> AsyncGenerator[str, None]:
        """
        恢复流式传输（断点续传）

        Args:
            message_id: 消息 ID
            from_sequence: 从哪个序列号开始恢复

        Yields:
            str: SSE 格式的事件
        """
        # 获取缓存的事件
        cached_events = await self.session_manager.get_cached_events(
            message_id,
            from_sequence
        )

        if not cached_events:
            # 没有缓存事件
            no_data_event = StreamEvent(
                event_type=StreamEventType.ERROR,
                content="没有找到可恢复的缓存数据",
                metadata={"message_id": message_id},
                message_id=message_id,
                sequence=0
            )
            yield no_data_event.to_sse()
            return

        # 发送缓存的事件
        for event in cached_events:
            yield event.to_sse()

        # 检查是否已完成
        last_event = cached_events[-1]
        if last_event.event_type == StreamEventType.COMPLETE:
            # 已经完成，不需要继续
            return

        # 如果未完成，通知前端需要重新请求
        resume_info_event = StreamEvent(
            event_type=StreamEventType.PROGRESS,
            content=f"已恢复到序列 {last_event.sequence}，请重新发起请求以继续",
            metadata={
                "message_id": message_id,
                "last_sequence": last_event.sequence,
                "need_restart": True
            },
            message_id=message_id,
            sequence=last_event.sequence + 1
        )

        yield resume_info_event.to_sse()


# 全局实例
_stream_session_manager: Optional[StreamSessionManager] = None
_stream_response_generator: Optional[StreamResponseGenerator] = None


def get_stream_session_manager() -> StreamSessionManager:
    """获取流式会话管理器"""
    global _stream_session_manager
    if _stream_session_manager is None:
        _stream_session_manager = StreamSessionManager()
    return _stream_session_manager


def get_stream_response_generator() -> StreamResponseGenerator:
    """获取流式响应生成器"""
    global _stream_response_generator
    if _stream_response_generator is None:
        _stream_response_generator = StreamResponseGenerator(
            session_manager=get_stream_session_manager()
        )
    return _stream_response_generator
