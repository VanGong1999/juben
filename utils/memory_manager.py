"""
增强版记忆管理器
管理用户画像、风格向量库和双层记忆系统

功能：
1. UserProfileManager: Redis存储用户偏好设置
2. StyleMemory: Milvus向量存储用户编辑过的风格片段
3. 🆕 UnifiedMemoryManager: 双层记忆系统（短期消息+中期记忆）
4. 🆕 TaskQueueManager: 任务队列管理器

"""

import json
import logging
import asyncio
import uuid
import threading
from typing import Dict, Any, List, Optional, Tuple, AsyncGenerator
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


# ==================== 用户画像管理 ====================

class LanguageStyle(Enum):
    """语言风格"""
    FORMAL = "formal"           # 正式
    CASUAL = "casual"           # 随意
    LITERARY = "literary"       # 文学性
    COLLOQUIAL = "colloquial"   # 口语化
    HUMOROUS = "humorous"       # 幽默
    DRAMATIC = "dramatic"       # 戏剧化


@dataclass
class UserProfile:
    """用户画像"""
    user_id: str

    # 偏好设置
    fav_genres: List[str] = field(default_factory=list)           # 偏好题材（如：都市、古装、悬疑、甜宠）
    avoid_tropes: List[str] = field(default_factory=list)         # 讨厌的桥段（如：三角恋、重生、穿越）
    language_style: List[str] = field(default_factory=list)       # 语言风格标签

    # 元数据
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # 统计信息
    total_edits: int = 0
    total_scripts: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserProfile':
        """从字典创建"""
        return cls(**data)


class UserProfileManager:
    """
    用户画像管理器

    使用 Redis 存储用户偏好设置
    Key 格式: user:{uid}:profile
    """

    def __init__(self, redis_client=None):
        """
        初始化用户画像管理器

        Args:
            redis_client: Redis客户端实例
        """
        self.redis_client = redis_client
        self.logger = logger
        self.key_prefix = "user"

    def _get_profile_key(self, user_id: str) -> str:
        """获取用户画像的Redis key"""
        return f"{self.key_prefix}:{user_id}:profile"

    async def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """
        获取用户画像

        Args:
            user_id: 用户ID

        Returns:
            UserProfile: 用户画像，如果不存在则返回None
        """
        try:
            if not self.redis_client:
                self.logger.warning("Redis客户端未配置，返回默认画像")
                return UserProfile(user_id=user_id)

            key = self._get_profile_key(user_id)
            data = await self.redis_client.get(key)

            if data:
                profile_data = json.loads(data)
                return UserProfile.from_dict(profile_data)
            else:
                return None

        except Exception as e:
            self.logger.error(f"获取用户画像失败 (user: {user_id}): {e}")
            return None

    async def create_profile(self, user_id: str) -> UserProfile:
        """
        创建新用户画像

        Args:
            user_id: 用户ID

        Returns:
            UserProfile: 新创建的用户画像
        """
        profile = UserProfile(user_id=user_id)
        await self.save_profile(profile)
        self.logger.info(f"✅ 创建用户画像 (user: {user_id})")
        return profile

    async def save_profile(self, profile: UserProfile) -> bool:
        """
        保存用户画像

        Args:
            profile: 用户画像对象

        Returns:
            bool: 是否保存成功
        """
        try:
            if not self.redis_client:
                self.logger.warning("Redis客户端未配置，跳过保存")
                return False

            profile.updated_at = datetime.now().isoformat()
            key = self._get_profile_key(profile.user_id)
            data = json.dumps(profile.to_dict(), ensure_ascii=False)

            await self.redis_client.set(key, data)
            self.logger.info(f"✅ 保存用户画像 (user: {profile.user_id})")
            return True

        except Exception as e:
            self.logger.error(f"保存用户画像失败 (user: {profile.user_id}): {e}")
            return False

    async def update_preferences(
        self,
        user_id: str,
        fav_genres: Optional[List[str]] = None,
        avoid_tropes: Optional[List[str]] = None,
        language_style: Optional[List[str]] = None
    ) -> bool:
        """
        更新用户偏好

        Args:
            user_id: 用户ID
            fav_genres: 偏好题材
            avoid_tropes: 讨厌的桥段
            language_style: 语言风格

        Returns:
            bool: 是否更新成功
        """
        try:
            # 获取或创建画像
            profile = await self.get_profile(user_id)
            if not profile:
                profile = await self.create_profile(user_id)

            # 更新字段
            if fav_genres is not None:
                profile.fav_genres = fav_genres
            if avoid_tropes is not None:
                profile.avoid_tropes = avoid_tropes
            if language_style is not None:
                profile.language_style = language_style

            return await self.save_profile(profile)

        except Exception as e:
            self.logger.error(f"更新用户偏好失败 (user: {user_id}): {e}")
            return False

    async def increment_edits(self, user_id: str) -> bool:
        """增加编辑次数"""
        profile = await self.get_profile(user_id)
        if profile:
            profile.total_edits += 1
            return await self.save_profile(profile)
        return False

    async def increment_scripts(self, user_id: str) -> bool:
        """增加剧本数量"""
        profile = await self.get_profile(user_id)
        if profile:
            profile.total_scripts += 1
            return await self.save_profile(profile)
        return False


# ==================== 风格向量库 ====================

@dataclass
class StyleFragment:
    """风格片段"""
    fragment_id: str
    user_id: str
    session_id: str

    # 内容
    original_text: str        # AI原文
    modified_text: str        # 用户修改后
    context: str              # 上下文

    # 分析结果
    intents: List[str]        # 修改意图
    features: List[str]       # 风格特征
    confidence: float         # 可信度

    # 元数据
    timestamp: str
    artifact_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class StyleMemory:
    """
    风格向量库

    使用 Milvus 存储用户编辑过的风格片段
    Collection: user_style_collection
    """

    def __init__(self, milvus_client=None, embedding_client=None):
        """
        初始化风格向量库

        Args:
            milvus_client: Milvus客户端
            embedding_client: 嵌入向量客户端
        """
        self.milvus_client = milvus_client
        self.embedding_client = embedding_client
        self.logger = logger
        self.collection_name = "user_style_collection"
        self.dimension = 768  # 默认向量维度

        # 初始化集合
        self._initialized = False

    async def _ensure_collection(self):
        """确保集合存在"""
        if self._initialized or not self.milvus_client:
            return

        try:
            from pymilvus import Collection, FieldSchema, CollectionSchema, DataType

            # 检查集合是否存在
            from pymilvus import utility
            if utility.has_collection(self.collection_name):
                self.collection = Collection(self.collection_name)
                self.logger.info(f"✅ 加载现有集合: {self.collection_name}")
            else:
                # 创建集合
                fields = [
                    FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=100, is_primary=True),
                    FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=100),
                    FieldSchema(name="session_id", dtype=DataType.VARCHAR, max_length=100),
                    FieldSchema(name="original_text", dtype=DataType.VARCHAR, max_length=8192),
                    FieldSchema(name="modified_text", dtype=DataType.VARCHAR, max_length=8192),
                    FieldSchema(name="context", dtype=DataType.VARCHAR, max_length=4096),
                    FieldSchema(name="intents", dtype=DataType.VARCHAR, max_length=500),
                    FieldSchema(name="features", dtype=DataType.VARCHAR, max_length=500),
                    FieldSchema(name="confidence", dtype=DataType.FLOAT),
                    FieldSchema(name="timestamp", dtype=DataType.VARCHAR, max_length=50),
                    FieldSchema(name="artifact_id", dtype=DataType.VARCHAR, max_length=100),
                    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dimension)
                ]

                schema = CollectionSchema(fields, description="用户风格片段向量库")
                self.collection = Collection(
                    name=self.collection_name,
                    schema=schema
                )

                # 创建索引
                index_params = {
                    "index_type": "IVF_FLAT",
                    "metric_type": "IP",  # 内积
                    "params": {"nlist": 128}
                }
                self.collection.create_index(field_name="embedding", index_params=index_params)

                self.logger.info(f"✅ 创建新集合: {self.collection_name}")

            self._initialized = True

        except ImportError:
            self.logger.warning("pymilvus未安装，风格向量库功能将不可用")
        except Exception as e:
            self.logger.error(f"初始化Milvus集合失败: {e}")

    async def save_fragment(
        self,
        fragment: StyleFragment
    ) -> bool:
        """
        保存风格片段

        Args:
            fragment: 风格片段

        Returns:
            bool: 是否保存成功
        """
        try:
            await self._ensure_collection()

            if not self.embedding_client or not self.milvus_client:
                self.logger.warning("嵌入向量或Milvus客户端未配置，跳过保存")
                return False

            # 生成嵌入向量
            embedding = await self._generate_embedding(fragment.modified_text)
            if embedding is None:
                return False

            # 插入数据
            data = [
                [fragment.fragment_id],
                [fragment.user_id],
                [fragment.session_id],
                [fragment.original_text],
                [fragment.modified_text],
                [fragment.context],
                [",".join(fragment.intents)],
                [",".join(fragment.features)],
                [fragment.confidence],
                [fragment.timestamp],
                [fragment.artifact_id or ""],
                [embedding]
            ]

            self.collection.insert(data)
            self.collection.flush()

            self.logger.info(f"✅ 保存风格片段 (fragment: {fragment.fragment_id}, user: {fragment.user_id})")
            return True

        except Exception as e:
            self.logger.error(f"保存风格片段失败: {e}")
            return False

    async def search_similar(
        self,
        query_text: str,
        user_id: str,
        top_k: int = 3
    ) -> List[StyleFragment]:
        """
        搜索相似的风格片段

        Args:
            query_text: 查询文本
            user_id: 用户ID
            top_k: 返回数量

        Returns:
            List[StyleFragment]: 相似的风格片段列表
        """
        try:
            await self._ensure_collection()

            if not self.embedding_client or not self.milvus_client:
                return []

            # 生成查询向量
            query_embedding = await self._generate_embedding(query_text)
            if query_embedding is None:
                return []

            # 加载集合
            self.collection.load()

            # 构建搜索过滤器（仅搜索该用户的片段）
            from pymilvus import AnnSearchRequest
            search_param = {
                "metric_type": "IP",
                "params": {"nprobe": 10}
            }

            # 执行搜索
            results = self.collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_param,
                limit=top_k,
                expr=f"user_id == '{user_id}'",
                output_fields=["user_id", "modified_text", "context", "intents", "features", "confidence"]
            )

            # 转换结果
            fragments = []
            for hit in results[0]:
                fragments.append(StyleFragment(
                    fragment_id=hit.id,
                    user_id=hit.entity.get("user_id"),
                    session_id=hit.entity.get("session_id", ""),
                    original_text=hit.entity.get("original_text", ""),
                    modified_text=hit.entity.get("modified_text", ""),
                    context=hit.entity.get("context", ""),
                    intents=hit.entity.get("intents", "").split(","),
                    features=hit.entity.get("features", "").split(","),
                    confidence=hit.entity.get("confidence", 0.0),
                    timestamp=hit.entity.get("timestamp", ""),
                    artifact_id=hit.entity.get("artifact_id")
                ))

            self.logger.info(f"✅ 搜索到 {len(fragments)} 个相似片段 (user: {user_id})")
            return fragments

        except Exception as e:
            self.logger.error(f"搜索相似片段失败: {e}")
            return []

    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """生成文本嵌入向量"""
        try:
            # 这里使用嵌入向量客户端
            # 如果没有配置，返回None
            if not self.embedding_client:
                self.logger.warning("嵌入向量客户端未配置")
                return None

            # 调用嵌入向量API
            embedding = await self.embedding_client.embed(text)
            return embedding

        except Exception as e:
            self.logger.error(f"生成嵌入向量失败: {e}")
            return None

    async def get_user_fragments(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[StyleFragment]:
        """
        获取用户的所有风格片段

        Args:
            user_id: 用户ID
            limit: 返回数量

        Returns:
            List[StyleFragment]: 风格片段列表
        """
        try:
            await self._ensure_collection()

            if not self.milvus_client:
                return []

            self.collection.load()

            # 查询用户的所有片段
            results = self.collection.query(
                expr=f"user_id == '{user_id}'",
                output_fields=["*"],
                limit=limit
            )

            fragments = []
            for item in results:
                fragments.append(StyleFragment(
                    fragment_id=item.get("id", ""),
                    user_id=item.get("user_id", ""),
                    session_id=item.get("session_id", ""),
                    original_text=item.get("original_text", ""),
                    modified_text=item.get("modified_text", ""),
                    context=item.get("context", ""),
                    intents=item.get("intents", "").split(","),
                    features=item.get("features", "").split(","),
                    confidence=item.get("confidence", 0.0),
                    timestamp=item.get("timestamp", ""),
                    artifact_id=item.get("artifact_id")
                ))

            return fragments

        except Exception as e:
            self.logger.error(f"获取用户片段失败: {e}")
            return []


# ==================== 全局实例 ====================

_user_profile_manager: Optional[UserProfileManager] = None
_style_memory: Optional[StyleMemory] = None


def get_user_profile_manager(redis_client=None) -> UserProfileManager:
    """获取用户画像管理器单例"""
    global _user_profile_manager
    if _user_profile_manager is None:
        _user_profile_manager = UserProfileManager(redis_client=redis_client)
    return _user_profile_manager


def get_style_memory(milvus_client=None, embedding_client=None) -> StyleMemory:
    """获取风格向量库单例"""
    global _style_memory
    if _style_memory is None:
        _style_memory = StyleMemory(
            milvus_client=milvus_client,
            embedding_client=embedding_client
        )
    return _style_memory



# ==================== 便捷函数 ====================

async def save_user_style_edit(
    user_id: str,
    session_id: str,
    original_text: str,
    modified_text: str,
    context: str,
    analysis_result: Dict[str, Any],
    artifact_id: Optional[str] = None
) -> bool:
    """
    保存用户风格编辑（便捷函数）

    Args:
        user_id: 用户ID
        session_id: 会话ID
        original_text: AI原文
        modified_text: 用户修改文
        context: 上下文
        analysis_result: 风格分析结果
        artifact_id: Artifact ID

    Returns:
        bool: 是否保存成功
    """
    import uuid
    style_memory = get_style_memory()

    fragment = StyleFragment(
        fragment_id=f"frag_{uuid.uuid4().hex[:16]}",
        user_id=user_id,
        session_id=session_id,
        original_text=original_text,
        modified_text=modified_text,
        context=context,
        intents=analysis_result.get("detected_intents", []),
        features=analysis_result.get("style_features", []),
        confidence=analysis_result.get("confidence_score", 0.0),
        timestamp=datetime.now().isoformat(),
        artifact_id=artifact_id
    )

    saved = await style_memory.save_fragment(fragment)

    # 整合归一：同步落一条用户级语义事实（style_example），作为新语义层的权威持久化。
    try:
        from utils.agent_memory import get_agent_memory_service

        get_agent_memory_service().record_user_style_example(
            user_id, modified_text or original_text, source="style_edit"
        )
    except Exception as e:
        logger.warning("同步 style_example 语义事实失败: %s", e)

    return saved


async def get_user_style_examples(
    user_id: str,
    query_text: str,
    count: int = 3
) -> List[str]:
    """
    获取用户风格示例（便捷函数）

    Args:
        user_id: 用户ID
        query_text: 查询文本
        count: 示例数量

    Returns:
        List[str]: 风格示例文本列表
    """
    style_memory = get_style_memory()
    fragments = await style_memory.search_similar(query_text, user_id, top_k=count)
    return [frag.modified_text for frag in fragments]


# ==================== 🆕 双层记忆系统 ====================

@dataclass
class ShortTermMemoryContext:
    """短期记忆上下文"""
    messages: List[Dict[str, Any]]  # 最近的消息列表
    formatted_context: str  # 格式化的上下文文本
    message_count: int  # 消息数量


@dataclass
class MiddleTermMemory:
    """中期记忆（Agent完成任务后的总结）"""
    memory_id: str
    user_id: str
    session_id: str
    agent_type: str  # Agent类型 (moved before optional fields)
    task_summary: str  # 任务总结
    compressed_summary: str  # 压缩后的摘要
    timestamp: datetime
    project_id: Optional[str] = None
    embedding: Optional[List[float]] = None  # 向量嵌入（用于检索）

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MiddleTermMemory':
        """从字典创建"""
        if isinstance(data.get('timestamp'), str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class UnifiedMemoryManager:
    """
    🆕 统一记忆管理器 - 双层记忆系统

    ，提供：
    1. 短期记忆：最近的消息历史（从Redis获取）
    2. 中期记忆：Agent完成任务后的总结（从向量库检索）

    使用场景：
    - Agent处理前调用 build_agent_context() 获取完整上下文
    - Agent完成后调用 process_agent_completion() 保存中期记忆
    """

    def __init__(self, storage_manager=None, redis_client=None, embedding_client=None):
        """
        初始化统一记忆管理器

        Args:
            storage_manager: 存储管理器（用于获取短期记忆）
            redis_client: Redis客户端（备用）
            embedding_client: 嵌入向量客户端（用于中期记忆检索）
        """
        from utils.storage_manager import get_storage
        self.storage_manager = storage_manager or get_storage()
        self.redis_client = redis_client or getattr(self.storage_manager, "redis_client", None)
        self.embedding_client = embedding_client
        self.logger = logger

    async def save_middle_term_memory(self, memory: MiddleTermMemory) -> bool:
        """保存中期记忆"""
        if not self.redis_client:
            self.logger.warning("Redis客户端未配置，无法保存中期记忆")
            return False

        try:
            from utils.memory_settings import get_memory_settings_manager
            settings = get_memory_settings_manager().get_settings(memory.user_id, memory.project_id)
            if not settings.effective_enabled:
                self.logger.info(f"记忆已关闭，跳过保存: user={memory.user_id}, project={memory.project_id}")
                return False
        except Exception:
            pass

        try:
            key = f"juben:middle_memory:{memory.user_id}:{memory.session_id}"
            await self.redis_client.lpush(key, json.dumps(memory.to_dict(), ensure_ascii=False))
            await self.redis_client.ltrim(key, 0, 199)  # 仅保留最近200条
            return True
        except Exception as e:
            self.logger.error(f"保存中期记忆失败: {e}")
            return False

    async def process_agent_completion(
        self,
        user_id: str,
        session_id: str,
        agent_type: str,
        task_summary: str,
        compressed_summary: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> bool:
        """处理Agent完成任务后的中期记忆保存"""
        try:
            memory = MiddleTermMemory(
                memory_id=f"mem_{uuid.uuid4().hex[:16]}",
                user_id=user_id,
                session_id=session_id,
                project_id=project_id,
                agent_type=agent_type,
                task_summary=task_summary,
                compressed_summary=compressed_summary or task_summary[:300],
                timestamp=datetime.now(),
            )
            return await self.save_middle_term_memory(memory)
        except Exception as e:
            self.logger.error(f"处理Agent完成任务失败: {e}")
            return False

    async def overwrite_middle_term_memories(
        self,
        user_id: str,
        session_id: str,
        memories: List[Dict[str, Any]]
    ) -> bool:
        """覆盖中期记忆（用于快照回滚）"""
        if not self.redis_client:
            return False
        try:
            key = f"juben:middle_memory:{user_id}:{session_id}"
            await self.redis_client.delete(key)
            if not memories:
                return True
            # 按时间从旧到新写入
            ordered = list(reversed(memories))
            for item in ordered:
                await self.redis_client.lpush(key, json.dumps(item, ensure_ascii=False))
            await self.redis_client.ltrim(key, 0, 199)
            return True
        except Exception as e:
            self.logger.error(f"覆盖中期记忆失败: {e}")
            return False

    async def clear_middle_term_memories(self, user_id: str, session_id: str) -> bool:
        if not self.redis_client:
            return False
        try:
            key = f"juben:middle_memory:{user_id}:{session_id}"
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            self.logger.error(f"清理中期记忆失败: {e}")
            return False

    async def build_agent_context(
        self,
        user_id: str,
        session_id: str,
        current_query: str,
        agent_type: str,
        short_term_limit: int = 10,
        middle_term_limit: int = 5
    ) -> Dict[str, Any]:
        """
        构建Agent上下文 - 双层记忆系统

        功能：
        - 短期记忆：获取最近的N条消息
        - 中期记忆：根据query检索相关的历史任务总结
        - 整合为完整的上下文返回给Agent

        Args:
            user_id: 用户ID
            session_id: 会话ID
            current_query: 当前查询
            agent_type: Agent类型
            short_term_limit: 短期记忆条数
            middle_term_limit: 中期记忆条数

        Returns:
            Dict: 包含短期记忆和中期记忆的上下文
        """
        try:
            self.logger.info(f"🔄 构建双层记忆上下文: {agent_type} - {user_id}")

            # 1. 获取短期记忆（最近的消息）
            short_term_context = await self._get_short_term_memory(
                user_id, session_id, short_term_limit
            )

            # 2. 获取中期记忆（相关的历史任务）
            middle_term_memories = await self._get_middle_term_memory(
                user_id, session_id, current_query, middle_term_limit
            )

            # 3. 构建完整上下文
            context = {
                "short_term_memory": {
                    "formatted_context": short_term_context.formatted_context,
                    "message_count": short_term_context.message_count,
                    "messages": short_term_context.messages
                },
                "middle_term_memory": {
                    "formatted_context": self._format_middle_memories(middle_term_memories),
                    "memory_count": len(middle_term_memories),
                    "memories": [m.to_dict() for m in middle_term_memories]
                },
                "stats": {
                    "short_term_count": short_term_context.message_count,
                    "middle_term_count": len(middle_term_memories),
                    "agent_type": agent_type,
                    "generated_at": datetime.now().isoformat()
                }
            }

            self.logger.info(f"✅ 双层记忆上下文构建完成: 消息:{short_term_context.message_count}条, 记忆:{len(middle_term_memories)}条")

            return context

        except Exception as e:
            self.logger.error(f"❌ 构建双层记忆上下文失败: {e}")
            return self._get_empty_context()

    async def get_memory_metrics(
        self,
        user_id: str,
        session_id: str,
        current_query: str = "",
        short_term_limit: int = 10,
        middle_term_limit: int = 5
    ) -> Dict[str, Any]:
        """
        评估记忆质量与覆盖情况（轻量指标）
        """
        try:
            short_term = await self._get_short_term_memory(user_id, session_id, short_term_limit)
            middle_term = await self._get_middle_term_memory(user_id, session_id, current_query, middle_term_limit)

            last_mid_ts = middle_term[0].timestamp.isoformat() if middle_term else None
            avg_mid_len = 0
            if middle_term:
                avg_mid_len = int(sum(len(m.task_summary or "") for m in middle_term) / len(middle_term))

            health = "healthy"
            warnings = []
            if short_term.message_count > 0 and len(middle_term) == 0:
                health = "degraded"
                warnings.append("存在对话但无中期记忆")
            if short_term.message_count > 30 and len(middle_term) < 3:
                health = "degraded"
                warnings.append("对话较长但中期记忆偏少")

            return {
                "health": health,
                "warnings": warnings,
                "short_term": {
                    "message_count": short_term.message_count,
                },
                "middle_term": {
                    "memory_count": len(middle_term),
                    "latest_timestamp": last_mid_ts,
                    "avg_summary_length": avg_mid_len
                }
            }
        except Exception as e:
            self.logger.error(f"获取记忆指标失败: {e}")
            return {
                "health": "unknown",
                "warnings": ["获取指标失败"],
                "short_term": {"message_count": 0},
                "middle_term": {"memory_count": 0}
            }

    async def _get_short_term_memory(
        self,
        user_id: str,
        session_id: str,
        limit: int
    ) -> ShortTermMemoryContext:
        """获取短期记忆"""
        try:
            # 从存储管理器获取最近的消息
            messages = await self.storage_manager.get_chat_messages(
                user_id=user_id,
                session_id=session_id,
                limit=limit
            )

            # 格式化上下文
            formatted_lines = []
            for msg in messages:
                role = msg.get('message_type', msg.get('role', 'unknown'))
                content = msg.get('content', '')
                if role == 'user':
                    formatted_lines.append(f"用户: {content}")
                elif role == 'assistant':
                    agent_name = msg.get('agent_name', 'AI')
                    formatted_lines.append(f"{agent_name}: {content}")

            formatted_context = "\n".join(formatted_lines) if formatted_lines else "暂无历史对话"

            return ShortTermMemoryContext(
                messages=messages,
                formatted_context=formatted_context,
                message_count=len(messages)
            )

        except Exception as e:
            self.logger.error(f"获取短期记忆失败: {e}")
            return ShortTermMemoryContext(
                messages=[],
                formatted_context="暂无历史对话",
                message_count=0
            )

    async def _get_middle_term_memory(
        self,
        user_id: str,
        session_id: str,
        query: str,
        limit: int
    ) -> List[MiddleTermMemory]:
        """获取中期记忆"""
        try:
            if not self.redis_client:
                return []

            key = f"juben:middle_memory:{user_id}:{session_id}"
            raw_items = await self.redis_client.lrange(key, 0, 200)
            if not raw_items:
                return []

            memories = []
            for raw in raw_items:
                try:
                    data = json.loads(raw)
                    memories.append(MiddleTermMemory.from_dict(data))
                except Exception:
                    continue

            if not query:
                return memories[:limit]

            query_terms = [t for t in query.lower().split() if t]

            def score(mem: MiddleTermMemory) -> int:
                text = f"{mem.task_summary} {mem.compressed_summary}".lower()
                return sum(1 for t in query_terms if t in text)

            memories.sort(key=score, reverse=True)
            return memories[:limit]

        except Exception as e:
            self.logger.error(f"获取中期记忆失败: {e}")
            return []

    async def get_middle_term_context(
        self,
        user_id: str,
        session_id: str,
        query: str,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        获取中期记忆上下文（格式化）

        Returns:
            Dict: { formatted_context, memory_count, memories }
        """
        memories = await self._get_middle_term_memory(user_id, session_id, query, limit)
        return {
            "formatted_context": self._format_middle_memories(memories),
            "memory_count": len(memories),
            "memories": [m.to_dict() for m in memories]
        }

    def _format_middle_memories(self, memories: List[MiddleTermMemory]) -> str:
        """格式化中期记忆为文本"""
        if not memories:
            return "暂无相关历史任务记录"

        formatted_lines = ["🧠 **中期记忆** (相关历史任务):"]

        for i, memory in enumerate(memories, 1):
            agent_type = memory.agent_type
            summary = memory.compressed_summary
            time_str = memory.timestamp.strftime("%m-%d %H:%M")

            formatted_lines.append(f"\n{i}. **{agent_type}** ({time_str})")
            formatted_lines.append(f"   {summary}")

        return "\n".join(formatted_lines)

    def _get_empty_context(self) -> Dict[str, Any]:
        """获取空上下文"""
        return {
            "short_term_memory": {
                "formatted_context": "暂无历史对话",
                "message_count": 0,
                "messages": []
            },
            "middle_term_memory": {
                "formatted_context": "暂无相关历史任务记录",
                "memory_count": 0,
                "memories": []
            },
            "stats": {
                "short_term_count": 0,
                "middle_term_count": 0,
                "agent_type": "unknown",
                "generated_at": datetime.now().isoformat()
            }
        }


# ==================== 🆕 任务队列管理器 ====================

@dataclass
class TaskItem:
    """任务项数据结构"""
    id: str
    action: str  # Agent类型或操作类型
    input: str
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[str] = None
    created_at: str = ""
    completed_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class TaskQueue:
    """任务队列数据结构"""
    queue_key: str  # user_id::session_id 格式
    user_id: str
    session_id: str
    tasks: List[TaskItem]
    current_task_index: int = 0
    created_at: str = ""
    last_accessed: str = ""
    original_user_query: str = ""  # 用户原始输入

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.last_accessed:
            self.last_accessed = datetime.now().isoformat()

    def get_current_task(self) -> Optional[TaskItem]:
        """获取当前任务"""
        self.last_accessed = datetime.now().isoformat()
        if self.current_task_index < len(self.tasks):
            return self.tasks[self.current_task_index]
        return None

    def mark_current_completed(self, result: str = ""):
        """标记当前任务完成"""
        self.last_accessed = datetime.now().isoformat()
        if self.current_task_index < len(self.tasks):
            task = self.tasks[self.current_task_index]
            task.status = "completed"
            task.result = result
            task.completed_at = datetime.now().isoformat()
            self.current_task_index += 1

    def has_pending_tasks(self) -> bool:
        """检查是否还有待执行任务"""
        return self.current_task_index < len(self.tasks)

    def is_empty(self) -> bool:
        """检查队列是否为空"""
        return len(self.tasks) == 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "queue_key": self.queue_key,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "tasks": [asdict(task) for task in self.tasks],
            "current_task_index": self.current_task_index,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "original_user_query": self.original_user_query
        }


class TaskQueueManager:
    """
    🆕 任务队列管理器

    ，支持：
    1. 任务队列创建和管理
    2. 内存缓存和文件持久化
    3. 任务执行状态追踪

    使用场景：
    - 多Agent工作流编排
    - 异步任务调度
    - 任务执行进度追踪
    """

    def __init__(self, persist_dir: str = "data/task_queues"):
        """
        初始化任务队列管理器

        Args:
            persist_dir: 持久化目录
        """
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        # 内存缓存
        self.memory_cache: Dict[str, TaskQueue] = {}
        self.cache_lock = threading.RLock()

        # 配置
        self.max_cache_size = 100  # 最大缓存队列数
        self.cache_ttl_hours = 2   # 缓存TTL（小时）
        self.logger = logger

    def _generate_queue_key(self, user_id: str, session_id: str) -> str:
        """生成队列唯一键"""
        return f"{user_id}::{session_id}"

    def _get_file_path(self, queue_key: str) -> Path:
        """获取队列文件路径"""
        safe_key = queue_key.replace("::", "_").replace("/", "_").replace("\\", "_")
        return self.persist_dir / f"{safe_key}.json"

    def _save_to_file(self, queue: TaskQueue):
        """保存队列到文件"""
        try:
            file_path = self._get_file_path(queue.queue_key)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(queue.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存队列文件失败: {e}")

    def _load_from_file(self, queue_key: str) -> Optional[TaskQueue]:
        """从文件加载队列"""
        try:
            file_path = self._get_file_path(queue_key)
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 重建TaskItem对象
                tasks = []
                for task_data in data.get('tasks', []):
                    tasks.append(TaskItem(**task_data))

                data['tasks'] = tasks
                return TaskQueue(**data)
        except Exception as e:
            self.logger.error(f"加载队列文件失败: {e}")
        return None

    def get_queue(self, user_id: str, session_id: str) -> Optional[TaskQueue]:
        """获取队列"""
        queue_key = self._generate_queue_key(user_id, session_id)

        with self.cache_lock:
            # 先检查内存缓存
            if queue_key in self.memory_cache:
                queue = self.memory_cache[queue_key]
                queue.last_accessed = datetime.now().isoformat()
                return queue

            # 从文件加载
            queue = self._load_from_file(queue_key)
            if queue:
                self._add_to_cache(queue_key, queue)
                queue.last_accessed = datetime.now().isoformat()

            return queue

    def save_queue(self, queue: TaskQueue):
        """保存队列"""
        with self.cache_lock:
            self._add_to_cache(queue.queue_key, queue)
            self._save_to_file(queue)

    def create_queue(
        self,
        user_id: str,
        session_id: str,
        tasks: List[TaskItem],
        original_user_query: str = ""
    ) -> TaskQueue:
        """创建新队列"""
        queue_key = self._generate_queue_key(user_id, session_id)
        queue = TaskQueue(
            queue_key=queue_key,
            user_id=user_id,
            session_id=session_id,
            tasks=tasks,
            original_user_query=original_user_query
        )

        self.save_queue(queue)
        return queue

    async def execute_queue(
        self,
        user_id: str,
        session_id: str,
        task_executor: Optional[Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        执行队列中的任务

        Args:
            user_id: 用户ID
            session_id: 会话ID

        Yields:
            Dict: 任务执行状态事件
        """
        queue = self.get_queue(user_id, session_id)
        if not queue:
            yield {
                "event_type": "error",
                "content": "任务队列不存在"
            }
            return

        try:
            while queue.has_pending_tasks():
                task = queue.get_current_task()
                if not task:
                    break

                # 更新任务状态
                task.status = "running"
                self.save_queue(queue)

                yield {
                    "event_type": "task_start",
                    "content": f"开始执行任务: {task.action}",
                    "metadata": {
                        "task_id": task.id,
                        "action": task.action,
                        "total_tasks": len(queue.tasks),
                        "current_index": queue.current_task_index + 1
                    }
                }

                # 执行任务（可注入执行器）
                result = ""
                if task_executor:
                    result = await task_executor(task)

                # 标记任务完成
                queue.mark_current_completed(result)
                self.save_queue(queue)

                yield {
                    "event_type": "task_complete",
                    "content": f"任务完成: {task.action}",
                    "metadata": {
                        "task_id": task.id,
                        "action": task.action,
                        "total_tasks": len(queue.tasks),
                        "current_index": queue.current_task_index
                    }
                }

            yield {
                "event_type": "queue_complete",
                "content": "所有任务执行完成"
            }

        except Exception as e:
            self.logger.error(f"执行任务队列失败: {e}")
            yield {
                "event_type": "error",
                "content": f"任务执行失败: {str(e)}"
            }

    def _add_to_cache(self, queue_key: str, queue: TaskQueue):
        """添加到内存缓存"""
        if len(self.memory_cache) >= self.max_cache_size:
            # 简单的LRU策略：删除第一个
            first_key = next(iter(self.memory_cache))
            del self.memory_cache[first_key]

        self.memory_cache[queue_key] = queue


# ==================== 🆕 全局实例 ====================

_unified_memory_manager: Optional[UnifiedMemoryManager] = None
_task_queue_manager: Optional[TaskQueueManager] = None


def get_unified_memory_manager() -> UnifiedMemoryManager:
    """获取统一记忆管理器单例"""
    global _unified_memory_manager
    if _unified_memory_manager is None:
        _unified_memory_manager = UnifiedMemoryManager()
    return _unified_memory_manager


def get_task_queue_manager() -> TaskQueueManager:
    """获取任务队列管理器单例"""
    global _task_queue_manager
    if _task_queue_manager is None:
        _task_queue_manager = TaskQueueManager()
    return _task_queue_manager
