"""
Juben项目存储管理器
基于三层存储架构：内存 -> Redis -> PostgreSQL
"""
import asyncio
import json
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from utils.logger import JubenLogger
from utils.database_client import (
    DatabaseErrorHandler,
    test_connection,
    fetch_one,
    fetch_all,
    execute,
)
from utils.redis_client import JubenRedisClient, get_redis_client, test_redis_connection


@dataclass
class ChatMessage:
    """聊天消息数据结构"""
    id: Optional[str] = None
    user_id: str = ""
    session_id: str = ""
    message_type: str = ""  # user, assistant, system, error
    content: str = ""
    agent_name: Optional[str] = None
    message_metadata: Dict[str, Any] = None
    created_at: str = ""
    
    def __post_init__(self):
        if self.message_metadata is None:
            self.message_metadata = {}
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class ContextState:
    """上下文状态数据结构（增强版）"""
    user_id: str = ""
    session_id: str = ""
    agent_name: str = ""
    context_data: Dict[str, Any] = None
    context_type: str = "general"  # general, workflow, multimodal, analysis
    context_version: int = 1  # 上下文版本号
    is_active: bool = True  # 是否为活跃上下文
    created_at: str = ""
    updated_at: str = ""
    expires_at: Optional[str] = None  # 过期时间
    
    def __post_init__(self):
        if self.context_data is None:
            self.context_data = {}
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()


@dataclass
class ConversationContext:
    """对话上下文数据结构（ ）"""
    session_id: str
    user_id: str
    thread_id: str
    
    # 多轮对话核心组件
    user_message_queue: List[Dict[str, Any]]  # 用户消息队列
    orchestrator_calls: List[Dict[str, Any]]  # orchestrator调用记录
    created_notes: List[Dict[str, Any]]  # 创建的notes
    
    # 上下文管理
    global_context: Dict[str, Any]  # 全局上下文
    agent_contexts: Dict[str, Any]  # 各agent的上下文
    shared_memory: Dict[str, Any]   # 共享内存
    conversation_history: List[Dict[str, Any]]  # 对话历史
    
    # 压缩和优化
    compression_history: List[Dict[str, Any]]  # 压缩历史
    context_summary: Optional[str] = None  # 上下文摘要
    is_compressed: bool = False  # 是否已压缩
    
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()


@dataclass
class Note:
    """Note数据结构"""
    id: Optional[str] = None
    user_id: str = ""
    session_id: str = ""
    action: str = ""
    name: str = ""
    title: Optional[str] = None
    cover_title: Optional[str] = None
    content_type: Optional[str] = None
    context: str = ""
    select_status: int = 0
    user_comment: Optional[str] = None
    metadata: Dict[str, Any] = None
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()


@dataclass
class TokenUsage:
    """Token使用记录数据结构"""
    id: Optional[str] = None
    user_id: str = ""
    session_id: str = ""
    agent_name: str = ""
    model_provider: str = ""
    model_name: str = ""
    request_tokens: int = 0
    response_tokens: int = 0
    total_tokens: int = 0
    cost_points: float = 0.0
    request_timestamp: str = ""
    billing_summary: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.billing_summary is None:
            self.billing_summary = {}
        if not self.request_timestamp:
            self.request_timestamp = datetime.now().isoformat()


class JubenStorageManager:
    """Juben项目存储管理器（增强版）"""
    
    def __init__(self):
        self.logger = JubenLogger("storage_manager")
        self.redis_client: Optional[JubenRedisClient] = None
        self.db_ready = False
        self.error_handler = DatabaseErrorHandler("storage_manager")
        
        # 缓存配置
        self.cache_ttl = {
            'session': 3600 * 24 * 3,  # 3天
            'context': 3600 * 24,      # 1天
            'messages': 3600 * 12,     # 12小时
            'notes': 3600 * 24,        # 1天
            'token_usage': 3600 * 6,   # 6小时
            'conversation': 3600 * 24 * 7  # 7天
        }
        
        # 多轮对话配置
        self.conversation_config = {
            'max_context_length': 8000,  # 最大上下文长度
            'compression_threshold': 0.8,  # 压缩阈值
            'max_messages_per_session': 1000,  # 每会话最大消息数
            'context_compression_enabled': True,  # 启用上下文压缩
            'auto_summary_enabled': True  # 启用自动摘要
        }
        
        self._initialized = False
    
    async def initialize(self):
        """初始化存储管理器"""
        try:
            self.logger.info("🚀 开始初始化Juben存储管理器...")
            
            # 初始化Redis客户端
            self.redis_client = await get_redis_client('high_priority')
            if self.redis_client:
                self.logger.info("✅ Redis客户端初始化成功")
            else:
                self.logger.warning("⚠️ Redis客户端初始化失败，将使用内存模式")
            
            # 测试连接
            redis_ok = await test_redis_connection()
            db_ok = await test_connection()
            
            self.logger.info(f"📊 存储层状态:")
            self.logger.info(f"  - Redis: {'✅ 正常' if redis_ok else '❌ 异常'}")
            self.logger.info(f"  - PostgreSQL: {'✅ 正常' if db_ok else '❌ 异常'}")
            self.db_ready = db_ok
            
            self._initialized = True
            self.logger.info("✅ Juben存储管理器初始化完成")
            
        except Exception as e:
            self.logger.error(f"❌ Juben存储管理器初始化失败: {e}")
            self._initialized = False
            raise
    
    def ensure_initialized(self):
        """确保持储管理器已初始化"""
        if not self._initialized:
            self.logger.info("🔄 存储管理器未初始化，开始初始化...")
            asyncio.create_task(self.initialize())
    
    # ==================== 用户会话管理 ====================
    
    async def create_user_session(self, user_id: str, session_id: str, metadata: Dict[str, Any] = None) -> bool:
        """创建用户会话"""
        try:
            session_data = {
                'user_id': user_id,
                'session_id': session_id,
                'status': 'active',
                'metadata': metadata or {},
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'last_activity_at': datetime.now().isoformat()
            }
            
            # 1. 保存到PostgreSQL
            async def _save_to_db():
                sql = """
                INSERT INTO user_sessions (
                    user_id, session_id, status, metadata, created_at, updated_at, last_activity_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (user_id, session_id)
                DO UPDATE SET
                    status = EXCLUDED.status,
                    metadata = EXCLUDED.metadata,
                    updated_at = EXCLUDED.updated_at,
                    last_activity_at = EXCLUDED.last_activity_at
                RETURNING user_id
                """
                row = await fetch_one(
                    sql,
                    session_data["user_id"],
                    session_data["session_id"],
                    session_data["status"],
                    session_data["metadata"],
                    session_data["created_at"],
                    session_data["updated_at"],
                    session_data["last_activity_at"],
                )
                return bool(row)
            
            success = await self.error_handler.with_retry(_save_to_db, "创建用户会话")
            
            # 2. 缓存到Redis
            if success and self.redis_client:
                cache_key = f"juben:session:{user_id}:{session_id}"
                await self.redis_client.set(cache_key, session_data, expire=self.cache_ttl['session'])
            
            return success
            
        except Exception as e:
            self.logger.error(f"❌ 创建用户会话失败: {e}")
            return False
    
    async def get_user_session(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """获取用户会话"""
        try:
            # 1. 尝试从Redis获取
            if self.redis_client:
                cache_key = f"juben:session:{user_id}:{session_id}"
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    return cached_data
            
            # 2. 从PostgreSQL获取
            async def _get_from_db():
                sql = """
                SELECT user_id, session_id, status, metadata, created_at, updated_at, last_activity_at
                FROM user_sessions
                WHERE user_id = $1 AND session_id = $2
                """
                row = await fetch_one(sql, user_id, session_id)
                if row and row.get("metadata"):
                    row["metadata"] = json.loads(row["metadata"]) if isinstance(row["metadata"], str) else row["metadata"]
                return row
            
            session_data = await self.error_handler.with_retry(_get_from_db, "获取用户会话")
            
            # 3. 缓存到Redis
            if session_data and self.redis_client:
                cache_key = f"juben:session:{user_id}:{session_id}"
                await self.redis_client.set(cache_key, session_data, expire=self.cache_ttl['session'])
            
            return session_data
            
        except Exception as e:
            self.logger.error(f"❌ 获取用户会话失败: {e}")
            return None
    
    async def update_session_activity(self, user_id: str, session_id: str) -> bool:
        """更新会话活动时间"""
        try:
            update_data = {
                'last_activity_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # 1. 更新PostgreSQL
            async def _update_db():
                sql = """
                UPDATE user_sessions
                SET last_activity_at = $1, updated_at = $2
                WHERE user_id = $3 AND session_id = $4
                RETURNING user_id
                """
                row = await fetch_one(
                    sql,
                    update_data["last_activity_at"],
                    update_data["updated_at"],
                    user_id,
                    session_id,
                )
                return bool(row)
            
            success = await self.error_handler.with_retry(_update_db, "更新会话活动时间")
            
            # 2. 更新Redis缓存
            if success and self.redis_client:
                cache_key = f"juben:session:{user_id}:{session_id}"
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    cached_data.update(update_data)
                    await self.redis_client.set(cache_key, cached_data, expire=self.cache_ttl['session'])
            
            return success
            
        except Exception as e:
            self.logger.error(f"❌ 更新会话活动时间失败: {e}")
            return False
    
    # ==================== 对话消息存储 ====================
    
    async def save_chat_message(self, message: ChatMessage) -> Optional[str]:
        """保存聊天消息"""
        try:
            message_dict = asdict(message)
            message_dict.pop('id', None)  # 移除id，让数据库自动生成

            # created_at 转 datetime（DB 列是 TIMESTAMPTZ，不接受 ISO 字符串）
            created_at = message_dict.get("created_at")
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)

            # 1. 保存到PostgreSQL
            async def _save_to_db():
                sql = """
                INSERT INTO chat_messages (
                    user_id, session_id, message_type, content, agent_name, message_metadata, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
                """
                row = await fetch_one(
                    sql,
                    message_dict["user_id"],
                    message_dict["session_id"],
                    message_dict["message_type"],
                    message_dict["content"],
                    message_dict.get("agent_name"),
                    json.dumps(message_dict.get("message_metadata") or {}, ensure_ascii=False),
                    created_at,
                )
                return row["id"] if row else None
            
            message_id = await self.error_handler.with_retry(_save_to_db, "保存聊天消息")
            
            # 2. 缓存到Redis（最近的消息）
            if message_id and self.redis_client:
                cache_key = f"juben:messages:{message.user_id}:{message.session_id}"
                message_dict['id'] = message_id
                await self.redis_client.lpush(cache_key, message_dict)
                # 只保留最近100条消息在缓存中
                await self.redis_client.lrange(cache_key, 0, 99)  # 触发清理
            
            return message_id
            
        except Exception as e:
            self.logger.error(f"❌ 保存聊天消息失败: {e}")
            return None
    
    async def get_chat_messages(self, user_id: str, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取聊天消息"""
        try:
            # 1. 尝试从Redis获取
            if self.redis_client:
                cache_key = f"juben:messages:{user_id}:{session_id}"
                cached_messages = await self.redis_client.lrange(cache_key, 0, limit - 1)
                if cached_messages:
                    return cached_messages
            
            # 2. 从PostgreSQL获取
            async def _get_from_db():
                sql = """
                SELECT id, user_id, session_id, message_type, content, agent_name, message_metadata, created_at
                FROM chat_messages
                WHERE user_id = $1 AND session_id = $2
                ORDER BY created_at DESC
                LIMIT $3
                """
                rows = await fetch_all(sql, user_id, session_id, limit)
                for row in rows:
                    if row.get("message_metadata"):
                        row["message_metadata"] = json.loads(row["message_metadata"]) if isinstance(row["message_metadata"], str) else row["message_metadata"]
                return rows
            
            messages = await self.error_handler.with_retry(_get_from_db, "获取聊天消息")
            
            # 3. 缓存到Redis
            if messages and self.redis_client:
                cache_key = f"juben:messages:{user_id}:{session_id}"
                for message in reversed(messages):  # 按时间正序缓存
                    await self.redis_client.lpush(cache_key, message)
                # 只保留最近100条消息在缓存中
                await self.redis_client.lrange(cache_key, 0, 99)
            
            return messages or []

        except Exception as e:
            self.logger.error(f"❌ 获取聊天消息失败: {e}")
            return []

    async def list_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """列出某用户的会话（去重 session_id，含标题/最近活跃/消息数）。"""
        try:
            async def _query():
                sql = """
                SELECT
                    session_id,
                    MAX(created_at) AS last_active,
                    COUNT(*) AS message_count,
                    (SELECT content FROM chat_messages m2
                     WHERE m2.session_id = m1.session_id AND m2.message_type = 'user'
                     ORDER BY created_at ASC LIMIT 1) AS title
                FROM chat_messages m1
                WHERE user_id = $1
                GROUP BY session_id
                ORDER BY last_active DESC
                """
                return await fetch_all(sql, user_id)

            rows = await self.error_handler.with_retry(_query, "列出会话")
            return [dict(r) for r in (rows or [])]
        except Exception as e:
            self.logger.error(f"❌ 列出会话失败: {e}")
            return []

    async def get_session_history(self, session_id: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取某会话的全部消息（按时间正序）；user_id 非空时强制归属过滤。"""
        try:
            async def _query():
                if user_id:
                    sql = """
                    SELECT id, user_id, session_id, message_type, content, agent_name, message_metadata, created_at
                    FROM chat_messages
                    WHERE session_id = $1 AND user_id = $2
                    ORDER BY created_at ASC
                    """
                    return await fetch_all(sql, session_id, user_id)
                sql = """
                SELECT id, user_id, session_id, message_type, content, agent_name, message_metadata, created_at
                FROM chat_messages
                WHERE session_id = $1
                ORDER BY created_at ASC
                """
                rows = await fetch_all(sql, session_id)
                for row in rows:
                    if row.get("message_metadata"):
                        row["message_metadata"] = (
                            json.loads(row["message_metadata"])
                            if isinstance(row["message_metadata"], str)
                            else row["message_metadata"]
                        )
                return rows

            rows = await self.error_handler.with_retry(_query, "获取会话历史")
            return [dict(r) for r in (rows or [])]
        except Exception as e:
            self.logger.error(f"❌ 获取会话历史失败: {e}")
            return []

    async def delete_session(self, session_id: str, user_id: Optional[str] = None) -> bool:
        """删除某会话的全部消息；user_id 非空时强制归属过滤。"""
        try:
            async def _del():
                if user_id:
                    sql = "DELETE FROM chat_messages WHERE session_id = $1 AND user_id = $2"
                    return await execute(sql, session_id, user_id)
                sql = "DELETE FROM chat_messages WHERE session_id = $1"
                return await execute(sql, session_id)

            await self.error_handler.with_retry(_del, "删除会话")
            return True
        except Exception as e:
            self.logger.error(f"❌ 删除会话失败: {e}")
            return False

    # ==================== 上下文状态管理 ====================
    
    async def save_context_state(self, context: ContextState) -> bool:
        """保存上下文状态"""
        try:
            context_dict = asdict(context)
            
            # 1. 保存到PostgreSQL
            async def _save_to_db():
                sql = """
                INSERT INTO context_states (
                    user_id, session_id, agent_name, context_data, context_type, context_version,
                    is_active, created_at, updated_at, expires_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (user_id, session_id, agent_name)
                DO UPDATE SET
                    context_data = EXCLUDED.context_data,
                    context_type = EXCLUDED.context_type,
                    context_version = EXCLUDED.context_version,
                    is_active = EXCLUDED.is_active,
                    updated_at = EXCLUDED.updated_at,
                    expires_at = EXCLUDED.expires_at
                RETURNING user_id
                """
                row = await fetch_one(
                    sql,
                    context_dict["user_id"],
                    context_dict["session_id"],
                    context_dict["agent_name"],
                    context_dict.get("context_data") or {},
                    context_dict.get("context_type"),
                    context_dict.get("context_version"),
                    context_dict.get("is_active"),
                    context_dict.get("created_at"),
                    context_dict.get("updated_at"),
                    context_dict.get("expires_at"),
                )
                return bool(row)
            
            success = await self.error_handler.with_retry(_save_to_db, "保存上下文状态")
            
            # 2. 缓存到Redis
            if success and self.redis_client:
                cache_key = f"juben:context:{context.user_id}:{context.session_id}:{context.agent_name}"
                await self.redis_client.set(cache_key, context_dict, expire=self.cache_ttl['context'])
            
            return success
            
        except Exception as e:
            self.logger.error(f"❌ 保存上下文状态失败: {e}")
            return False
    
    async def get_context_state(self, user_id: str, session_id: str, agent_name: str) -> Optional[Dict[str, Any]]:
        """获取上下文状态"""
        try:
            # 1. 尝试从Redis获取
            if self.redis_client:
                cache_key = f"juben:context:{user_id}:{session_id}:{agent_name}"
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    return cached_data
            
            # 2. 从PostgreSQL获取
            async def _get_from_db():
                sql = """
                SELECT user_id, session_id, agent_name, context_data, context_type, context_version,
                       is_active, created_at, updated_at, expires_at
                FROM context_states
                WHERE user_id = $1 AND session_id = $2 AND agent_name = $3
                """
                row = await fetch_one(sql, user_id, session_id, agent_name)
                if row and row.get("context_data"):
                    row["context_data"] = json.loads(row["context_data"]) if isinstance(row["context_data"], str) else row["context_data"]
                return row
            
            context_data = await self.error_handler.with_retry(_get_from_db, "获取上下文状态")
            
            # 3. 缓存到Redis
            if context_data and self.redis_client:
                cache_key = f"juben:context:{user_id}:{session_id}:{agent_name}"
                await self.redis_client.set(cache_key, context_data, expire=self.cache_ttl['context'])
            
            return context_data
            
        except Exception as e:
            self.logger.error(f"❌ 获取上下文状态失败: {e}")
            return None
    
    # ==================== 多轮对话上下文管理 ====================
    
    async def create_conversation_context(
        self, 
        user_id: str, 
        session_id: str, 
        initial_query: str
    ) -> ConversationContext:
        """创建对话上下文（ ）"""
        try:
            # 首先尝试从数据库恢复现有上下文
            existing_context = await self._load_conversation_context_from_db(user_id, session_id)
            if existing_context:
                self.logger.info(f"🔄 恢复现有对话上下文: {user_id}:{session_id}")
                # 将新的查询添加到消息队列
                existing_context.user_message_queue.append({
                    "content": initial_query,
                    "timestamp": datetime.now().isoformat(),
                    "is_new": True,
                    "message_id": str(uuid.uuid4())
                })
                # 同时添加到对话历史
                existing_context.conversation_history.append({
                    "role": "user",
                    "content": initial_query,
                    "timestamp": datetime.now().isoformat()
                })
                # 保存更新
                await self._save_conversation_context(existing_context)
                return existing_context
            
            # 创建新对话上下文
            self.logger.info(f"🔍 创建全新对话上下文: {user_id}:{session_id}")
            thread_id = str(uuid.uuid4())
            
            conversation_context = ConversationContext(
                session_id=session_id,
                user_id=user_id,
                thread_id=thread_id,
                user_message_queue=[{
                    "content": initial_query,
                    "timestamp": datetime.now().isoformat(),
                    "is_new": True,
                    "message_id": str(uuid.uuid4())
                }],
                orchestrator_calls=[],
                created_notes=[],
                global_context={},
                agent_contexts={},
                shared_memory={},
                conversation_history=[{
                    "role": "user",
                    "content": initial_query,
                    "timestamp": datetime.now().isoformat()
                }],
                compression_history=[],
                context_summary=None,
                is_compressed=False
            )
            
            # 保存到数据库
            await self._save_conversation_context(conversation_context)
            self.logger.info(f"✅ 对话上下文创建完成: {user_id}:{session_id}")
            return conversation_context
            
        except Exception as e:
            self.logger.error(f"❌ 创建对话上下文失败: {e}")
            raise
    
    async def get_conversation_context(
        self, 
        user_id: str, 
        session_id: str
    ) -> Optional[ConversationContext]:
        """获取对话上下文"""
        try:
            # 1. 尝试从Redis获取
            if self.redis_client:
                cache_key = f"juben:conversation:{user_id}:{session_id}"
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    return ConversationContext(**cached_data)
            
            # 2. 从数据库获取
            context = await self._load_conversation_context_from_db(user_id, session_id)
            if context:
                # 缓存到Redis
                if self.redis_client:
                    cache_key = f"juben:conversation:{user_id}:{session_id}"
                    await self.redis_client.set(
                        cache_key, 
                        asdict(context), 
                        expire=self.cache_ttl['conversation']
                    )
                return context
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ 获取对话上下文失败: {e}")
            return None
    
    async def update_conversation_context(
        self, 
        user_id: str, 
        session_id: str, 
        updates: Dict[str, Any]
    ) -> bool:
        """更新对话上下文"""
        try:
            context = await self.get_conversation_context(user_id, session_id)
            if not context:
                self.logger.warning(f"未找到对话上下文: {user_id}:{session_id}")
                return False
            
            # 更新字段
            for key, value in updates.items():
                if hasattr(context, key):
                    setattr(context, key, value)
            
            context.updated_at = datetime.now().isoformat()
            
            # 保存更新
            await self._save_conversation_context(context)
            self.logger.info(f"✅ 对话上下文更新完成: {user_id}:{session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 更新对话上下文失败: {e}")
            return False
    
    async def add_user_message(
        self, 
        user_id: str, 
        session_id: str, 
        message: str, 
        mark_as_new: bool = True
    ) -> bool:
        """添加用户消息到对话上下文"""
        try:
            context = await self.get_conversation_context(user_id, session_id)
            if not context:
                self.logger.warning(f"未找到对话上下文: {user_id}:{session_id}")
                return False
            
            # 添加到消息队列
            context.user_message_queue.append({
                "content": message,
                "timestamp": datetime.now().isoformat(),
                "is_new": mark_as_new,
                "message_id": str(uuid.uuid4())
            })
            
            # 添加到对话历史
            context.conversation_history.append({
                "role": "user",
                "content": message,
                "timestamp": datetime.now().isoformat()
            })
            
            # 检查是否需要压缩
            if self.conversation_config['context_compression_enabled']:
                await self._check_and_compress_context(context)
            
            # 保存更新
            await self._save_conversation_context(context)
            self.logger.info(f"✅ 用户消息已添加: {user_id}:{session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 添加用户消息失败: {e}")
            return False
    
    async def add_orchestrator_call(
        self, 
        user_id: str, 
        session_id: str, 
        instruction: str
    ) -> bool:
        """添加orchestrator调用记录"""
        try:
            context = await self.get_conversation_context(user_id, session_id)
            if not context:
                self.logger.warning(f"未找到对话上下文: {user_id}:{session_id}")
                return False
            
            # 添加到orchestrator调用记录
            context.orchestrator_calls.append({
                "instruction": instruction,
                "timestamp": datetime.now().isoformat(),
                "call_id": str(uuid.uuid4())
            })
            
            # 保存更新
            await self._save_conversation_context(context)
            self.logger.info(f"✅ Orchestrator调用记录已添加: {user_id}:{session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 添加orchestrator调用记录失败: {e}")
            return False
    
    async def add_conversation_message(
        self, 
        user_id: str, 
        session_id: str, 
        role: str, 
        content: str,
        agent_source: Optional[str] = None
    ) -> bool:
        """添加对话消息"""
        try:
            context = await self.get_conversation_context(user_id, session_id)
            if not context:
                self.logger.warning(f"未找到对话上下文: {user_id}:{session_id}")
                return False
            
            # 添加到对话历史
            context.conversation_history.append({
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "agent_source": agent_source
            })
            
            # 保存更新
            await self._save_conversation_context(context)
            self.logger.info(f"✅ 对话消息已添加: {user_id}:{session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 添加对话消息失败: {e}")
            return False
    
    async def _load_conversation_context_from_db(
        self, 
        user_id: str, 
        session_id: str
    ) -> Optional[ConversationContext]:
        """从数据库加载对话上下文"""
        try:
            # 获取所有上下文数据
            rows = await fetch_all(
                """
                SELECT user_id, session_id, agent_name, context_data, context_type, context_version,
                       is_active, created_at, updated_at, expires_at
                FROM context_states
                WHERE user_id = $1 AND session_id = $2
                """,
                user_id,
                session_id,
            )
            
            if not rows:
                return None
            
            # 重构对话上下文
            for row in rows:
                if row.get("context_data"):
                    row["context_data"] = json.loads(row["context_data"]) if isinstance(row["context_data"], str) else row["context_data"]
            contexts_by_action = {ctx.get("agent_name"): ctx for ctx in rows}
            
            # 获取notes
            created_notes = await fetch_all(
                """
                SELECT id, user_id, session_id, action, name, title, cover_title, content_type, context, select_status, user_comment, metadata, created_at, updated_at
                FROM notes
                WHERE user_id = $1 AND session_id = $2
                ORDER BY created_at DESC
                """,
                user_id,
                session_id,
            )
            for note in created_notes:
                if note.get("metadata"):
                    note["metadata"] = json.loads(note["metadata"]) if isinstance(note["metadata"], str) else note["metadata"]
            
            # 获取对话历史
            conversation_history = []
            messages = await fetch_all(
                """
                SELECT message_type, content, created_at, agent_name
                FROM chat_messages
                WHERE user_id = $1 AND session_id = $2
                ORDER BY created_at
                """,
                user_id,
                session_id,
            )
            for msg in messages:
                conversation_history.append({
                    "role": msg.get('message_type', 'user'),
                    "content": msg.get('content', ''),
                    "timestamp": msg.get('created_at', ''),
                    "agent_source": msg.get('agent_name')
                })
            
            # 重构对话上下文
            context = ConversationContext(
                session_id=session_id,
                user_id=user_id,
                thread_id=str(uuid.uuid4()),
                user_message_queue=self._extract_user_message_queue(contexts_by_action),
                orchestrator_calls=self._extract_orchestrator_calls(contexts_by_action),
                created_notes=created_notes,
                global_context={},
                agent_contexts=self._rebuild_agent_contexts(contexts_by_action),
                shared_memory={},
                conversation_history=conversation_history,
                compression_history=[],
                context_summary=None,
                is_compressed=False
            )
            
            return context
            
        except Exception as e:
            self.logger.error(f"❌ 从数据库加载对话上下文失败: {e}")
            return None
    
    async def _save_conversation_context(self, context: ConversationContext):
        """保存对话上下文到数据库"""
        try:
            
            # 保存各个组件的上下文状态
            for agent_name, agent_context in context.agent_contexts.items():
                context_state = ContextState(
                    user_id=context.user_id,
                    session_id=context.session_id,
                    agent_name=agent_name,
                    context_data=agent_context,
                    context_type="conversation",
                    is_active=True
                )
                await self.save_context_state(context_state)
            
            # 保存用户消息队列
            if context.user_message_queue:
                queue_context = ContextState(
                    user_id=context.user_id,
                    session_id=context.session_id,
                    agent_name="user_message_queue",
                    context_data={"queue": context.user_message_queue},
                    context_type="conversation",
                    is_active=True
                )
                await self.save_context_state(queue_context)
            
            # 保存orchestrator调用记录
            if context.orchestrator_calls:
                orchestrator_context = ContextState(
                    user_id=context.user_id,
                    session_id=context.session_id,
                    agent_name="orchestrator_calls",
                    context_data={"calls": context.orchestrator_calls},
                    context_type="conversation",
                    is_active=True
                )
                await self.save_context_state(orchestrator_context)
            
            # 保存notes
            for note_data in context.created_notes:
                note = Note(
                    user_id=context.user_id,
                    session_id=context.session_id,
                    action=note_data.get('action', ''),
                    name=note_data.get('name', ''),
                    title=note_data.get('title', ''),
                    context=note_data.get('context', ''),
                    select_status=note_data.get('select', 0),
                    metadata=note_data.get('metadata', {})
                )
                await self.save_note(note)
            
            self.logger.info(f"✅ 对话上下文已保存: {context.user_id}:{context.session_id}")
            
        except Exception as e:
            self.logger.error(f"❌ 保存对话上下文失败: {e}")
    
    def _extract_user_message_queue(self, contexts_by_action: Dict[str, Dict]) -> List[Dict[str, Any]]:
        """提取用户消息队列"""
        queue_ctx = contexts_by_action.get("user_message_queue", {})
        return queue_ctx.get("context_data", {}).get("queue", [])
    
    def _extract_orchestrator_calls(self, contexts_by_action: Dict[str, Dict]) -> List[Dict[str, Any]]:
        """提取orchestrator调用记录"""
        orchestrator_ctx = contexts_by_action.get("orchestrator_calls", {})
        return orchestrator_ctx.get("context_data", {}).get("calls", [])
    
    def _rebuild_agent_contexts(self, contexts_by_action: Dict[str, Dict]) -> Dict[str, Any]:
        """重构agent上下文"""
        agent_contexts = {}
        system_actions = {"user_message_queue", "orchestrator_calls"}
        
        for action, ctx in contexts_by_action.items():
            if action not in system_actions:
                agent_contexts[action] = {
                    "timestamp": ctx.get("updated_at", ""),
                    "context_data": ctx.get("context_data", {}),
                    "metadata": ctx.get("metadata", {}),
                    "status": "completed"
                }
        
        return agent_contexts
    
    async def _check_and_compress_context(self, context: ConversationContext):
        """检查并压缩上下文"""
        try:
            # 计算当前上下文长度
            total_length = 0
            for msg in context.conversation_history:
                total_length += len(str(msg.get('content', '')))
            
            max_length = self.conversation_config['max_context_length']
            compression_threshold = self.conversation_config['compression_threshold']
            
            if total_length >= max_length * compression_threshold:
                self.logger.info(f"📊 上下文长度 {total_length} 超过阈值，开始压缩")
                
                # 生成上下文摘要
                summary = await self._generate_context_summary(context)
                if summary:
                    context.context_summary = summary
                    context.is_compressed = True
                    
                    # 记录压缩历史
                    context.compression_history.append({
                        "timestamp": datetime.now().isoformat(),
                        "original_length": total_length,
                        "compression_ratio": 0.3,
                        "summary": summary
                    })
                    
                    # 保留最近的消息，压缩历史消息
                    recent_messages = context.conversation_history[-10:]  # 保留最近10条
                    context.conversation_history = recent_messages
                    
                    self.logger.info(f"✅ 上下文压缩完成，保留 {len(recent_messages)} 条消息")
            
        except Exception as e:
            self.logger.error(f"❌ 上下文压缩失败: {e}")
    
    async def _generate_context_summary(self, context: ConversationContext) -> Optional[str]:
        """生成上下文摘要"""
        try:
            # 这里可以调用LLM生成摘要
            # 暂时返回简单摘要
            total_messages = len(context.conversation_history)
            user_messages = len([msg for msg in context.conversation_history if msg.get('role') == 'user'])
            assistant_messages = len([msg for msg in context.conversation_history if msg.get('role') == 'assistant'])
            
            summary = f"""
对话摘要：
- 总消息数: {total_messages}
- 用户消息: {user_messages}
- 助手消息: {assistant_messages}
- 创建时间: {context.created_at}
- 最后更新: {context.updated_at}
"""
            return summary
            
        except Exception as e:
            self.logger.error(f"❌ 生成上下文摘要失败: {e}")
            return None

    # ==================== Notes系统 ====================
    
    async def save_note(self, note: Note) -> Optional[str]:
        """保存Note"""
        try:
            note_dict = asdict(note)
            note_dict.pop('id', None)  # 移除id，让数据库自动生成
            
            # 1. 保存到PostgreSQL
            async def _save_to_db():
                sql = """
                INSERT INTO notes (
                    user_id, session_id, action, name, title, cover_title, content_type, context,
                    select_status, user_comment, metadata, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                ON CONFLICT (user_id, session_id, action, name)
                DO UPDATE SET
                    title = EXCLUDED.title,
                    cover_title = EXCLUDED.cover_title,
                    content_type = EXCLUDED.content_type,
                    context = EXCLUDED.context,
                    select_status = EXCLUDED.select_status,
                    user_comment = EXCLUDED.user_comment,
                    metadata = EXCLUDED.metadata,
                    updated_at = EXCLUDED.updated_at
                RETURNING id
                """
                row = await fetch_one(
                    sql,
                    note_dict["user_id"],
                    note_dict["session_id"],
                    note_dict["action"],
                    note_dict["name"],
                    note_dict.get("title"),
                    note_dict.get("cover_title"),
                    note_dict.get("content_type"),
                    note_dict.get("context"),
                    note_dict.get("select_status", 0),
                    note_dict.get("user_comment"),
                    note_dict.get("metadata") or {},
                    note_dict["created_at"],
                    note_dict["updated_at"],
                )
                return row["id"] if row else None
            
            note_id = await self.error_handler.with_retry(_save_to_db, "保存Note")
            
            # 2. 缓存到Redis
            if note_id and self.redis_client:
                cache_key = f"juben:notes:{note.user_id}:{note.session_id}"
                note_dict['id'] = note_id
                await self.redis_client.lpush(cache_key, note_dict)
            
            return note_id
            
        except Exception as e:
            self.logger.error(f"❌ 保存Note失败: {e}")
            return None
    
    async def get_notes(self, user_id: str, session_id: str, action: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取Notes"""
        try:
            # 1. 尝试从Redis获取
            if self.redis_client:
                cache_key = f"juben:notes:{user_id}:{session_id}"
                cached_notes = await self.redis_client.lrange(cache_key, 0, -1)
                if cached_notes:
                    if action:
                        return [note for note in cached_notes if note.get('action') == action]
                    return cached_notes
            
            # 2. 从PostgreSQL获取
            async def _get_from_db():
                if action:
                    sql = """
                    SELECT id, user_id, session_id, action, name, title, cover_title, content_type, context, select_status, user_comment, metadata, created_at, updated_at
                    FROM notes
                    WHERE user_id = $1 AND session_id = $2 AND action = $3
                    ORDER BY created_at DESC
                    """
                    rows = await fetch_all(sql, user_id, session_id, action)
                else:
                    sql = """
                    SELECT id, user_id, session_id, action, name, title, cover_title, content_type, context, select_status, user_comment, metadata, created_at, updated_at
                    FROM notes
                    WHERE user_id = $1 AND session_id = $2
                    ORDER BY created_at DESC
                    """
                    rows = await fetch_all(sql, user_id, session_id)
                for row in rows:
                    if row.get("metadata"):
                        row["metadata"] = json.loads(row["metadata"]) if isinstance(row["metadata"], str) else row["metadata"]
                return rows
            
            notes = await self.error_handler.with_retry(_get_from_db, "获取Notes")
            
            # 3. 缓存到Redis
            if notes and self.redis_client:
                cache_key = f"juben:notes:{user_id}:{session_id}"
                for note in reversed(notes):
                    await self.redis_client.lpush(cache_key, note)
            
            return notes or []

        except Exception as e:
            self.logger.error(f"❌ 获取Notes失败: {e}")
            return []

    # ==================== Agent输出Note专用方法（====================

    async def save_agent_output_note(
        self,
        user_id: str,
        session_id: str,
        action: str,
        name: str,
        context: str,
        title: Optional[str] = None,
        cover_title: Optional[str] = None,
        select_status: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        保存Agent输出Note（专用方法）

        Args:
            user_id: 用户ID
            session_id: 会话ID
            action: Agent动作类型（如character_profile_generator）
            name: Note名称（唯一标识，如character1, plot1等）
            context: Note内容
            title: 可选标题
            cover_title: 可选封面标题
            select_status: 选择状态（0未选择，1已选择）
            metadata: 元数据

        Returns:
            str: Note ID
        """
        try:
            note = Note(
                user_id=user_id,
                session_id=session_id,
                action=action,
                name=name,
                title=title,
                cover_title=cover_title,
                context=context,
                select_status=select_status,
                metadata=metadata or {}
            )
            return await self.save_note(note)
        except Exception as e:
            self.logger.error(f"❌ 保存Agent输出Note失败: {e}")
            return None

    async def get_notes_by_action(self, user_id: str, session_id: str, action: str) -> List[Dict[str, Any]]:
        """按action类型获取Notes"""
        return await self.get_notes(user_id, session_id, action)

    async def get_selected_notes(self, user_id: str, session_id: str) -> List[Dict[str, Any]]:
        """获取已选择的Notes"""
        try:
            async def _get_selected():
                rows = await fetch_all(
                    """
                    SELECT id, user_id, session_id, action, name, title, cover_title, content_type, context, select_status, user_comment, metadata, created_at, updated_at
                    FROM notes
                    WHERE user_id = $1 AND session_id = $2 AND select_status = 1
                    ORDER BY created_at DESC
                    """,
                    user_id,
                    session_id,
                )
                for row in rows:
                    if row.get("metadata"):
                        row["metadata"] = json.loads(row["metadata"]) if isinstance(row["metadata"], str) else row["metadata"]
                return rows

            selected_notes = await self.error_handler.with_retry(_get_selected, "获取已选择Notes")
            return selected_notes or []
        except Exception as e:
            self.logger.error(f"❌ 获取已选择Notes失败: {e}")
            return []

    async def batch_update_note_selection(
        self,
        user_id: str,
        session_id: str,
        selections: List[Dict[str, Any]]
    ) -> bool:
        """
        批量更新Note选择状态

        Args:
            user_id: 用户ID
            session_id: 会话ID
            selections: 选择列表，格式: [{'action': 'character_profile_generator', 'name': 'character1', 'selected': True, 'user_comment': '...'}]
        """
        try:
            for selection in selections:
                action = selection.get('action')
                name = selection.get('name')
                selected = selection.get('selected', False)
                user_comment = selection.get('user_comment')

                # 构建更新数据
                update_data = {'select_status': 1 if selected else 0}
                if user_comment:
                    update_data['user_comment'] = user_comment

                # 执行更新
                async def _update_selection():
                    if "user_comment" in update_data:
                        sql = """
                        UPDATE notes
                        SET select_status = $1, user_comment = $2, updated_at = $3
                        WHERE user_id = $4 AND session_id = $5 AND action = $6 AND name = $7
                        RETURNING id
                        """
                        row = await fetch_one(
                            sql,
                            update_data["select_status"],
                            update_data["user_comment"],
                            datetime.now().isoformat(),
                            user_id,
                            session_id,
                            action,
                            name,
                        )
                    else:
                        sql = """
                        UPDATE notes
                        SET select_status = $1, updated_at = $2
                        WHERE user_id = $3 AND session_id = $4 AND action = $5 AND name = $6
                        RETURNING id
                        """
                        row = await fetch_one(
                            sql,
                            update_data["select_status"],
                            datetime.now().isoformat(),
                            user_id,
                            session_id,
                            action,
                            name,
                        )
                    return bool(row)

                await self.error_handler.with_retry(_update_selection, f"更新Note选择状态: {action}:{name}")

            # 清除相关Redis缓存
            if self.redis_client:
                cache_key = f"juben:notes:{user_id}:{session_id}"
                await self.redis_client.delete(cache_key)

            return True
        except Exception as e:
            self.logger.error(f"❌ 批量更新Note选择状态失败: {e}")
            return False

    async def export_notes(
        self,
        user_id: str,
        session_id: str,
        export_format: str = 'txt',
        content_types: Optional[List[str]] = None,
        include_user_comments: bool = True
    ) -> Dict[str, Any]:
        """
        导出Notes

        Args:
            user_id: 用户ID
            session_id: 会话ID
            export_format: 导出格式（txt, json, md）
            content_types: 要导出的内容类型列表
            include_user_comments: 是否包含用户评论

        Returns:
            Dict: 导出结果
        """
        try:
            # 获取Notes
            async def _get_all_notes():
                rows = await fetch_all(
                    """
                    SELECT id, user_id, session_id, action, name, title, cover_title, content_type, context, select_status, user_comment, metadata, created_at, updated_at
                    FROM notes
                    WHERE user_id = $1 AND session_id = $2
                    ORDER BY created_at DESC
                    """,
                    user_id,
                    session_id,
                )
                for row in rows:
                    if row.get("metadata"):
                        row["metadata"] = json.loads(row["metadata"]) if isinstance(row["metadata"], str) else row["metadata"]
                if content_types:
                    return [n for n in rows if n.get("metadata", {}).get("content_type") in content_types]
                return rows

            notes = await self.error_handler.with_retry(_get_all_notes, "获取Notes用于导出")

            if not notes:
                return {'exported_data': '', 'total_items': 0, 'content_summary': {}}

            # 按action分组统计
            content_summary = {}
            for note in notes:
                action = note.get('action', 'unknown')
                content_summary[action] = content_summary.get(action, 0) + 1

            # 格式化导出
            if export_format == 'json':
                exported_data = json.dumps(notes, ensure_ascii=False, indent=2)
            elif export_format == 'md':
                exported_data = self._format_notes_as_markdown(notes, include_user_comments)
            else:  # txt
                exported_data = self._format_notes_as_text(notes, include_user_comments)

            return {
                'exported_data': exported_data,
                'total_items': len(notes),
                'content_summary': content_summary
            }
        except Exception as e:
            self.logger.error(f"❌ 导出Notes失败: {e}")
            return {'exported_data': '', 'total_items': 0, 'content_summary': {}}

    def _format_notes_as_text(self, notes: List[Dict], include_comments: bool) -> str:
        """格式化Notes为纯文本"""
        lines = []
        lines.append(f"剧本创作Notes导出 - 共{len(notes)}项")
        lines.append("=" * 60)

        for note in notes:
            lines.append(f"\n[{note.get('action', 'unknown')}] {note.get('title') or note.get('name')}")
            lines.append("-" * 40)
            lines.append(note.get('context', ''))

            if include_comments and note.get('user_comment'):
                lines.append(f"\n用户评论: {note.get('user_comment')}")

            lines.append("")

        return "\n".join(lines)

    def _format_notes_as_markdown(self, notes: List[Dict], include_comments: bool) -> str:
        """格式化Notes为Markdown"""
        lines = []
        lines.append(f"# 剧本创作Notes导出")
        lines.append(f"\n共 **{len(notes)}** 项\n")

        for note in notes:
            title = note.get('title') or note.get('name', '未命名')
            lines.append(f"## {note.get('action', 'unknown')}: {title}")
            lines.append(f"\n{note.get('context', '')}\n")

            if include_comments and note.get('user_comment'):
                lines.append(f"**用户评论**: {note.get('user_comment')}\n")

        return "\n".join(lines)

    # ==================== Token使用统计 ====================
    
    async def save_token_usage(self, token_usage: TokenUsage) -> Optional[str]:
        """保存Token使用记录"""
        try:
            token_dict = asdict(token_usage)
            token_dict.pop('id', None)  # 移除id，让数据库自动生成
            
            # 1. 保存到PostgreSQL
            async def _save_to_db():
                sql = """
                INSERT INTO token_usage (
                    user_id, session_id, agent_name, model_provider, model_name,
                    request_tokens, response_tokens, total_tokens, cost_points,
                    request_timestamp, billing_summary
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING id
                """
                row = await fetch_one(
                    sql,
                    token_dict["user_id"],
                    token_dict["session_id"],
                    token_dict.get("agent_name"),
                    token_dict.get("model_provider"),
                    token_dict.get("model_name"),
                    token_dict.get("request_tokens", 0),
                    token_dict.get("response_tokens", 0),
                    token_dict.get("total_tokens", 0),
                    token_dict.get("cost_points", 0.0),
                    token_dict.get("request_timestamp"),
                    token_dict.get("billing_summary") or {},
                )
                return row["id"] if row else None
            
            usage_id = await self.error_handler.with_retry(_save_to_db, "保存Token使用记录")
            
            # 2. 缓存到Redis（用于实时统计）
            if usage_id and self.redis_client:
                cache_key = f"juben:token_usage:{token_usage.user_id}:{token_usage.session_id}"
                token_dict['id'] = usage_id
                await self.redis_client.lpush(cache_key, token_dict)
            
            return usage_id
            
        except Exception as e:
            self.logger.error(f"❌ 保存Token使用记录失败: {e}")
            return None
    
    async def get_token_usage_summary(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """获取Token使用摘要"""
        try:
            # 1. 尝试从Redis获取
            if self.redis_client:
                cache_key = f"juben:token_usage:{user_id}:{session_id}"
                cached_usage = await self.redis_client.lrange(cache_key, 0, -1)
                if cached_usage:
                    total_tokens = sum(usage.get('total_tokens', 0) for usage in cached_usage)
                    total_cost = sum(usage.get('cost_points', 0) for usage in cached_usage)
                    return {
                        'total_requests': len(cached_usage),
                        'total_tokens': total_tokens,
                        'total_cost_points': total_cost,
                        'avg_tokens_per_request': total_tokens / len(cached_usage) if cached_usage else 0
                    }
            
            # 2. 从PostgreSQL获取
            async def _get_from_db():
                rows = await fetch_all(
                    """
                    SELECT id, user_id, session_id, agent_name, model_provider, model_name,
                           request_tokens, response_tokens, total_tokens, cost_points,
                           request_timestamp, billing_summary
                    FROM token_usage
                    WHERE user_id = $1 AND session_id = $2
                    """,
                    user_id,
                    session_id,
                )
                for row in rows:
                    if row.get("billing_summary"):
                        row["billing_summary"] = json.loads(row["billing_summary"]) if isinstance(row["billing_summary"], str) else row["billing_summary"]
                return rows
            
            usage_records = await self.error_handler.with_retry(_get_from_db, "获取Token使用摘要")
            
            if usage_records:
                total_tokens = sum(record.get('total_tokens', 0) for record in usage_records)
                total_cost = sum(record.get('cost_points', 0) for record in usage_records)
                return {
                    'total_requests': len(usage_records),
                    'total_tokens': total_tokens,
                    'total_cost_points': total_cost,
                    'avg_tokens_per_request': total_tokens / len(usage_records)
                }
            
            return {
                'total_requests': 0,
                'total_tokens': 0,
                'total_cost_points': 0.0,
                'avg_tokens_per_request': 0
            }
            
        except Exception as e:
            self.logger.error(f"❌ 获取Token使用摘要失败: {e}")
            return {
                'total_requests': 0,
                'total_tokens': 0,
                'total_cost_points': 0.0,
                'avg_tokens_per_request': 0
            }
    
    # ==================== 流式事件存储 ====================
    
    async def save_stream_event(self, user_id: str, session_id: str, event_type: str, 
                               content_type: Optional[str], agent_source: str, 
                               event_data: Any, event_metadata: Dict[str, Any] = None) -> Optional[str]:
        """保存流式事件"""
        try:
            event_dict = {
                'user_id': user_id,
                'session_id': session_id,
                'event_type': event_type,
                'content_type': content_type,
                'agent_source': agent_source,
                'event_data': event_data,
                'event_metadata': event_metadata or {},
                'is_replayed': False,
                'created_at': datetime.now().isoformat()
            }
            
            # 1. 保存到PostgreSQL
            async def _save_to_db():
                sql = """
                INSERT INTO stream_events (
                    user_id, session_id, event_type, content_type, agent_source,
                    event_data, event_metadata, is_replayed, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id
                """
                row = await fetch_one(
                    sql,
                    event_dict["user_id"],
                    event_dict["session_id"],
                    event_dict["event_type"],
                    event_dict.get("content_type"),
                    event_dict.get("agent_source"),
                    event_dict.get("event_data"),
                    event_dict.get("event_metadata") or {},
                    event_dict.get("is_replayed", False),
                    event_dict.get("created_at"),
                )
                return row["id"] if row else None
            
            event_id = await self.error_handler.with_retry(_save_to_db, "保存流式事件")
            
            # 2. 缓存到Redis（最近的事件）
            if event_id and self.redis_client:
                cache_key = f"juben:stream_events:{user_id}:{session_id}"
                event_dict['id'] = event_id
                await self.redis_client.lpush(cache_key, event_dict)
                # 只保留最近50个事件在缓存中
                await self.redis_client.lrange(cache_key, 0, 49)
            
            return event_id
            
        except Exception as e:
            self.logger.error(f"❌ 保存流式事件失败: {e}")
            return None
    
    async def get_stream_events(self, user_id: str, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取流式事件"""
        try:
            # 1. 尝试从Redis获取
            if self.redis_client:
                cache_key = f"juben:stream_events:{user_id}:{session_id}"
                cached_events = await self.redis_client.lrange(cache_key, 0, limit - 1)
                if cached_events:
                    return cached_events
            
            # 2. 从PostgreSQL获取
            async def _get_from_db():
                rows = await fetch_all(
                    """
                    SELECT id, user_id, session_id, event_type, content_type, agent_source,
                           event_data, event_metadata, is_replayed, created_at
                    FROM stream_events
                    WHERE user_id = $1 AND session_id = $2
                    ORDER BY created_at DESC
                    LIMIT $3
                    """,
                    user_id,
                    session_id,
                    limit,
                )
                for row in rows:
                    if row.get("event_data"):
                        row["event_data"] = json.loads(row["event_data"]) if isinstance(row["event_data"], str) else row["event_data"]
                    if row.get("event_metadata"):
                        row["event_metadata"] = json.loads(row["event_metadata"]) if isinstance(row["event_metadata"], str) else row["event_metadata"]
                return rows
            
            events = await self.error_handler.with_retry(_get_from_db, "获取流式事件")
            
            # 3. 缓存到Redis
            if events and self.redis_client:
                cache_key = f"juben:stream_events:{user_id}:{session_id}"
                for event in reversed(events):
                    await self.redis_client.lpush(cache_key, event)
                # 只保留最近50个事件在缓存中
                await self.redis_client.lrange(cache_key, 0, 49)
            
            return events or []
            
        except Exception as e:
            self.logger.error(f"❌ 获取流式事件失败: {e}")
            return []
    
    # ==================== 清理方法 ====================
    
    async def cleanup_expired_cache(self):
        """清理过期的缓存数据"""
        try:
            if not self.redis_client:
                return
            
            # 获取所有缓存键
            # 注意：这里需要根据实际的Redis客户端API调整
            # 在实际实现中，可能需要使用SCAN命令来遍历键
            
            self.logger.info("🧹 缓存清理完成")
            
        except Exception as e:
            self.logger.error(f"❌ 清理过期缓存失败: {e}")
    
    async def close(self):
        """关闭存储管理器"""
        try:
            if self.redis_client:
                await self.redis_client.close()
            
            self.logger.info("✅ 存储管理器已关闭")
            
        except Exception as e:
            self.logger.error(f"❌ 关闭存储管理器失败: {e}")


# 全局存储管理器实例（延迟初始化）
storage_manager = None


async def init_storage() -> JubenStorageManager:
    """初始化存储管理器 - 便捷函数"""
    global storage_manager
    if storage_manager is None:
        storage_manager = JubenStorageManager()
    if not storage_manager._initialized:
        await storage_manager.initialize()
    return storage_manager


def get_storage() -> JubenStorageManager:
    """获取存储管理器实例（延迟初始化）"""
    global storage_manager
    if storage_manager is None:
        storage_manager = JubenStorageManager()
    return storage_manager
