"""
竖屏短剧策划助手 - 基础Agent类
提供统一的Agent基础功能
抽象出公用的方法

🔧 生产级优化版本 - 2025
"""
import os
import asyncio
import logging
import time
import random
import re
import uuid
from abc import ABC, abstractmethod
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from typing import AsyncGenerator, Dict, Any, List, Optional, Union, Callable
from datetime import datetime, timedelta, timezone
from functools import wraps, lru_cache
from pathlib import Path
import json

# 重试机制支持
try:
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_exponential,
        retry_if_exception_type,
        before_sleep_log
    )
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False
    # 定义装饰器占位符
    def retry(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

try:
    from config.settings import JubenSettings
    from utils.logger import JubenLogger
    from utils.zhipu_search import zhipu_search
    from utils.knowledge_base_client import KnowledgeBaseClient
    from utils.token_accumulator import TokenUsage, create_token_accumulator, add_token_usage, get_billing_summary
    from utils.langsmith_client import create_langsmith_llm_client
    from utils.storage_manager import get_storage, ChatMessage, ContextState, Note
    from utils.agent_output_storage import get_agent_output_storage
    from utils.performance_monitor import get_performance_monitor, PerformanceContext
    from utils.project_manager import get_project_manager
    from utils.enhanced_context_manager import EnhancedContextManager, get_enhanced_context_manager
    from utils.context_mixin import ContextManagementMixin
    from utils.structured_output_guard import StructuredOutputGuard
    from utils.agent_naming import canonical_agent_id, AGENT_CATEGORY_MAPPING, OUTPUT_TAG_PHASE_MAPPING
    from utils.memory_manager import get_unified_memory_manager, get_user_profile_manager
    from utils.memory_settings import get_memory_settings_manager
    from utils.output_schema_registry import get_output_schema_registry
    from services.output_archive_service import OutputArchiveService
    from utils.project_types import FileType
except ImportError:
    # 处理相对导入问题
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from config.settings import JubenSettings
    from utils.logger import JubenLogger
    from utils.zhipu_search import zhipu_search
    from utils.knowledge_base_client import KnowledgeBaseClient
    from utils.token_accumulator import TokenUsage, create_token_accumulator, add_token_usage, get_billing_summary
    from utils.langsmith_client import create_langsmith_llm_client
    from utils.storage_manager import get_storage, ChatMessage, ContextState, Note
    from utils.agent_output_storage import get_agent_output_storage
    from utils.performance_monitor import get_performance_monitor, PerformanceContext
    from utils.project_manager import get_project_manager
    from utils.enhanced_context_manager import EnhancedContextManager, get_enhanced_context_manager
    from utils.context_mixin import ContextManagementMixin
    from utils.structured_output_guard import StructuredOutputGuard
    from utils.agent_naming import canonical_agent_id, AGENT_CATEGORY_MAPPING, OUTPUT_TAG_PHASE_MAPPING
    from utils.memory_manager import get_unified_memory_manager, get_user_profile_manager
    from utils.memory_settings import get_memory_settings_manager
    from utils.output_schema_registry import get_output_schema_registry
    from services.output_archive_service import OutputArchiveService
    from utils.project_types import FileType


class BaseJubenAgent(ABC, ContextManagementMixin):
    """
    竖屏短剧策划助手基础Agent类
     
    
    核心功能：
    1. 统一的LLM调用接口
    2. 智谱搜索集成
    3. 知识库检索
    4. 流式输出支持
    5. 错误处理和重试机制
    6. 日志记录和Token统计
    7. 🚀 连接池管理（新增）
    8. 🧠 性能优化配置（新增）
    9. 🛑 停止管理机制（新增）
    10. 🎯 多模态处理（新增）
    11. 📝 Notes系统（新增）
    12. 🔍 智能引用解析（新增）
    13. 🔄 增强型上下文管理（新增）- 滚动窗口、智能摘要、语义分块
    """
    
    # 类级别的连接池管理器，所有juben agents共享
    _connection_pool_manager = None
    # 🔧 使用asyncio.Lock确保线程安全
    _pool_manager_lock = asyncio.Lock()
    # 🔧 类级别logger用于类方法
    _class_logger: Optional[logging.Logger] = None

    def __init__(self, agent_name: str, model_provider: str = "deepseek", enable_enhanced_context: bool = False):
        """
        初始化基础Agent

        Args:
            agent_name: Agent名称
            model_provider: 模型提供商
            enable_enhanced_context: 是否启用增强上下文管理（RAG、智能选择等）
        """
        # 调用父类初始化（包括ContextManagementMixin）
        super().__init__(agent_name, model_provider)

        self.agent_name = agent_name
        self.agent_id = canonical_agent_id(agent_name)
        self.model_provider = model_provider
        self.config = JubenSettings()
        self.logger = JubenLogger(f"Agent.{agent_name}", level=self.config.log_level)

        # 🆕 【新增】增强上下文管理配置
        self.enable_enhanced_context = enable_enhanced_context
        self.enable_auto_rag = getattr(self.config, 'enable_auto_rag', False)  # 是否启用RAG自动加载
        self.enable_smart_select = getattr(self.config, 'enable_smart_select', False)  # 是否启用智能选择
        self.enable_scratchpad = getattr(self.config, 'enable_scratchpad', False)  # 是否启用草稿纸
        self.max_rag_items = getattr(self.config, 'max_rag_items', 3)  # 最大RAG条目数
        self.context_pack_enabled = getattr(self.config, 'context_pack_enabled', True)
        self.context_pack_max_chars = getattr(self.config, 'context_pack_max_chars', 2000)
        self.context_tail_max_chars = getattr(self.config, 'context_tail_max_chars', 600)
        self.context_middle_term_limit = getattr(self.config, 'context_middle_term_limit', 5)

        # 🆕 【新增】项目管理器
        self.project_manager = None
        self._init_project_manager()

        # 🚀 【性能优化配置】从全局配置中读取性能设置
        self.enable_thought_streaming = getattr(self.config, 'enable_thought_streaming', True)
        self.thought_min_length = getattr(self.config, 'thought_min_length', 20)
        self.thought_batch_size = getattr(self.config, 'thought_batch_size', 5)
        self.enable_fast_mode = getattr(self.config, 'enable_fast_mode', False)
        
        # Token累加器相关
        self.current_token_accumulator_key = None
        
        # 性能监控器
        self.performance_monitor = get_performance_monitor()
        
        # 🚀 【优化】使用连接池管理器替代直接客户端
        self.redis_client = None
        self._redis_pool_type = self._determine_redis_pool_type()
        
        # 🎯 流式事件存储相关
        self._stream_storage_enabled = True
        self._current_user_id = None
        self._current_session_id = None
        self._current_project_id = None
        
        # 🔧 断网检测日志去重机制 - 使用OrderedDict限制大小
        self._last_disconnect_log_time = OrderedDict()  # session_id -> timestamp
        self._disconnect_log_interval = 60  # 60秒内不重复输出断网日志
        
        # 🆕 【新增】Notes系统集成
        self.notes_manager = None
        self._init_notes_manager()
        
        # 🆕 【新增】智能引用解析器
        self.reference_resolver = None
        self._init_reference_resolver()
        
        # 🆕 【新增】多模态处理器
        self.multimodal_processor = None
        self._init_multimodal_processor()
        
        # 🆕 【新增】停止管理器
        self.stop_manager = None
        self._init_stop_manager()

        # 🆕 【新增】反馈追踪支持
        self._current_trace_id = None
        self._trace_tracking_enabled = True
        self._output_schema: Optional[Dict[str, Any]] = None
        self._output_constraint_template: Optional[str] = None

        # 初始化客户端
        self._init_clients()
        self.structured_output_guard = StructuredOutputGuard()
        self._rag_trace: List[Dict[str, Any]] = []
        
        # 加载系统提示词
        self._load_system_prompt()

        # 🆕 【新增】增强上下文管理日志
        if self.enable_enhanced_context:
            self.logger.info(f"🧠 增强上下文管理: 已启用")
            self.logger.info(f"   - RAG自动加载: {'✓' if self.enable_auto_rag else '✗'}")
            self.logger.info(f"   - 智能上下文选择: {'✓' if self.enable_smart_select else '✗'}")
            self.logger.info(f"   - 草稿纸机制: {'✓' if self.enable_scratchpad else '✗'}")

        self.logger.info(f"初始化{agent_name}成功")
        self.logger.info(f"🚀 性能优化配置: 思考过程流式输出={'开启' if self.enable_thought_streaming else '关闭'}")
        self.logger.info(f"🔧 Redis连接池类型: {self._redis_pool_type}")
        self.logger.info(f"✅ 支持连接池管理、性能优化、停止控制、Notes系统、智能引用解析和增强型上下文管理")
    
    def _determine_redis_pool_type(self) -> str:
        """根据agent类型确定Redis连接池优先级"""
        # orchestrator和concierge使用高优先级连接池
        if 'orchestrator' in self.agent_name.lower() or 'concierge' in self.agent_name.lower():
            return 'high_priority'
        # 其他agents使用普通连接池
        return 'normal'
    
    @classmethod
    async def get_connection_pool_manager(cls):
        """
        🔧 获取连接池管理器实例（线程安全版）

        使用asyncio.Lock确保在并发环境下只初始化一次
        """
        # 🔧 使用双重检查锁定模式优化性能
        if cls._connection_pool_manager is not None:
            return cls._connection_pool_manager

        async with cls._pool_manager_lock:
            # 🔧 双重检查：等待锁后再次检查
            if cls._connection_pool_manager is not None:
                return cls._connection_pool_manager

            try:
                from utils.connection_pool_manager import get_connection_pool_manager
                cls._connection_pool_manager = await get_connection_pool_manager()

                # 🔧 使用logging模块而不是不存在的cls.logger
                if cls._class_logger is None:
                    cls._class_logger = logging.getLogger(__name__)
                cls._class_logger.info("✅ 连接池管理器初始化成功")

            except ImportError as e:
                if cls._class_logger is None:
                    cls._class_logger = logging.getLogger(__name__)
                cls._class_logger.warning(f"⚠️ 连接池管理器不可用: {e}")
                cls._connection_pool_manager = None
            except Exception as e:
                if cls._class_logger is None:
                    cls._class_logger = logging.getLogger(__name__)
                cls._class_logger.error(f"❌ 连接池管理器初始化失败: {e}")
                cls._connection_pool_manager = None

        return cls._connection_pool_manager
    
    def _init_notes_manager(self):
        """🆕 初始化Notes管理器"""
        try:
            from utils.notes_manager import get_notes_manager
            self.notes_manager = get_notes_manager()
            self.logger.info("✅ Notes管理器初始化成功")
        except ImportError as e:
            self.logger.warning(f"❌ Notes管理器初始化失败: {e}")
            self.notes_manager = None
    
    def _init_reference_resolver(self):
        """🆕 初始化智能引用解析器"""
        try:
            from utils.reference_resolver import get_juben_reference_resolver
            self.reference_resolver = get_juben_reference_resolver()
            self.logger.info("✅ 智能引用解析器初始化成功")
        except ImportError as e:
            self.logger.warning(f"❌ 智能引用解析器初始化失败: {e}")
            self.reference_resolver = None
    
    def _init_multimodal_processor(self):
        """🆕 初始化多模态处理器"""
        try:
            from utils.multimodal_processor import get_multimodal_processor
            self.multimodal_processor = get_multimodal_processor()
            self.logger.info("✅ 多模态处理器初始化成功")
        except ImportError as e:
            self.logger.warning(f"❌ 多模态处理器初始化失败: {e}")
            self.multimodal_processor = None
    
    def _init_stop_manager(self):
        """停止管理器是 async 单例，延迟到使用时 await 初始化（见 check_stop_status 等）。"""
        self.stop_manager = None

    def _init_project_manager(self):
        """🆕 初始化项目管理器"""
        try:
            self.project_manager = get_project_manager()
            self.logger.info("✅ 项目管理器初始化成功")
        except ImportError as e:
            self.logger.warning(f"❌ 项目管理器初始化失败: {e}")
            self.project_manager = None
        except Exception as e:
            self.logger.warning(f"❌ 项目管理器初始化异常: {e}")
            self.project_manager = None

    def get_thinking_budget(self) -> int:
        """
        🧠 根据agent类型返回对应的thinking_budget配置
        
        创作类agent和hitpoint agent使用512，其他agent使用128
        
        Returns:
            int: 对应的thinking_budget值
        """
        # 🎯 创作类和hitpoint agent使用高thinking_budget (512)
        high_budget_agents = {
            'short_drama_creator_agent',     # 短剧创作
            'story_outline_evaluation_agent', # 故事大纲评估
            'character_profile_agent',       # 角色开发
            'plot_points_workflow_agent',    # 情节点工作流
            'juben_orchestrator',            # 编排器
        }
        
        if self.agent_name in high_budget_agents:
            thinking_budget = 500
            self.logger.debug(f"🧠 {self.agent_name} 使用高thinking_budget: {thinking_budget}")
        else:
            thinking_budget = 128
            self.logger.debug(f"🧠 {self.agent_name} 使用标准thinking_budget: {thinking_budget}")
        
        return thinking_budget

    def get_agent_temperature(self) -> float:
        """
        🌡️ 根据agent类型返回对应的temperature配置
        
        不同类型的agent需要不同的创造性水平：
        - orchestrator: 0.5 (需要一定创造性来做决策，但保持逻辑性)
        - concierge: 0.4 (稳定的理解和回应)
        - knowledge: 0.3 (更准确和客观的信息)
        - 创作类agent: 0.6 (需要更多创造性)
        - 评估类agent: 0.2 (需要更客观和准确)
        - 其余的: 0.4 (默认值)
        
        Returns:
            float: 对应的temperature值
        """
        # 🎯 创作类agent使用高temperature (0.6)
        high_temperature_agents = {
            'short_drama_creator_agent',     # 短剧创作
            'character_profile_agent',        # 角色开发
            'plot_points_workflow_agent',    # 情节点工作流
            'story_outline_evaluation_agent' # 故事大纲评估
        }
        
        # 🧠 orchestrator使用中等偏高temperature (0.5)
        if self.agent_name == 'juben_orchestrator':
            temperature = 0.5
            self.logger.debug(f"🌡️ {self.agent_name} 使用orchestrator专用temperature: {temperature}")
        
        # 🎭 concierge使用中等temperature (0.4)
        elif self.agent_name == 'juben_concierge':
            temperature = 0.4
            self.logger.debug(f"🌡️ {self.agent_name} 使用concierge专用temperature: {temperature}")
        
        # 📚 knowledge使用低temperature (0.3)
        elif 'knowledge' in self.agent_name.lower():
            temperature = 0.3
            self.logger.debug(f"🌡️ {self.agent_name} 使用knowledge专用temperature: {temperature}")
        
        # 🎨 创作类agent使用高temperature (0.6)
        elif self.agent_name in high_temperature_agents:
            temperature = 0.6
            self.logger.debug(f"🌡️ {self.agent_name} 使用创作类专用temperature: {temperature}")
        
        # 🔧 其他agent使用默认temperature (0.4)
        else:
            temperature = 0.4
            self.logger.debug(f"🌡️ {self.agent_name} 使用默认temperature: {temperature}")
        
        return temperature

    def _get_llm_kwargs(self, **extra_kwargs):
        """
        🎯 【通用LLM参数管理】根据当前LLM提供商和agent类型智能调整参数
        
        thinking_budget参数仅在Gemini中有效，OpenAI/Claude/通义千问等不支持
        现在还会根据agent类型设置不同的temperature值
        """
        kwargs = {}
        
        # 🌡️ 【新增】根据agent类型设置temperature
        agent_temperature = self.get_agent_temperature()
        kwargs["temperature"] = agent_temperature
        
        # 检查当前使用的LLM提供商
        if hasattr(self.llm_client, 'provider') and self.llm_client.provider == "gemini":
            # 🧠 Gemini支持thinking_budget，使用agent特定的配置
            thinking_budget = self.get_thinking_budget()
            kwargs["thinking_budget"] = thinking_budget
            self.logger.debug(f"🧠 Gemini客户端，{self.agent_name}使用thinking_budget={thinking_budget}, temperature={agent_temperature}")
        else:
            # 其他提供商不支持thinking_budget
            self.logger.debug(f"💡 {self.agent_name}使用temperature={agent_temperature}，当前提供商不支持thinking_budget参数")
        
        # 添加其他额外参数（如果用户传入了temperature，会覆盖agent默认设置）
        kwargs.update(extra_kwargs)
        return kwargs
    
    async def should_emit_thought(self, content: str = "") -> bool:
        """
        判断是否应该发送思考过程事件
        
        Args:
            content: 思考内容
            
        Returns:
            bool: 是否应该发送
        """
        # 🚀 【性能优化】根据全局配置决定是否发送思考过程
        if not self.enable_thought_streaming:
            return False
        
        # 如果开启了思考过程，使用配置的过滤逻辑
        if len(content.strip()) < self.thought_min_length:  # 使用配置的最小长度
            return False
            
        return True
    
    async def _get_redis_client(self):
        """🚀 【优化】获取Redis客户端，使用连接池管理器"""
        try:
            if self.redis_client is None:
                pool_manager = await self.get_connection_pool_manager()
                if pool_manager:
                    self.redis_client = await pool_manager.get_redis_client(self._redis_pool_type)
                    self.logger.debug(f"🔧 {self.agent_name} 获取Redis客户端成功 (pool_type={self._redis_pool_type})")
                else:
                    # 回退到原始方式
                    from utils.redis_client import get_redis_client
                    self.redis_client = await get_redis_client()
                    self.logger.debug(f"🔧 {self.agent_name} 使用原始Redis客户端")
            
            return self.redis_client
            
        except Exception as e:
            self.logger.error(f"❌ {self.agent_name} 获取Redis客户端失败: {e}")
            # 回退到原始方式
            if self.redis_client is None:
                try:
                    from utils.redis_client import get_redis_client
                    self.redis_client = await get_redis_client()
                except ImportError:
                    self.logger.warning(f"⚠️ Redis客户端不可用，跳过Redis功能")
                    return None
            return self.redis_client
    
    async def _get_db_client(self, client_type: str = 'normal'):
        """🚀 【新增】获取数据库客户端，使用连接池管理器"""
        try:
            # 当前使用PostgreSQL连接池
            from utils.database_client import get_postgres_pool
            return await get_postgres_pool()
        except Exception as e:
            self.logger.error(f"❌ {self.agent_name} 获取数据库客户端失败: {e}")
            return None
    
    async def get_connection_stats(self) -> Dict[str, Any]:
        """🚀 【新增】获取当前agent的连接池统计信息"""
        try:
            pool_manager = await self.get_connection_pool_manager()
            if pool_manager:
                return await pool_manager.get_connection_stats()
            else:
                return {'error': '连接池管理器不可用'}
        except Exception as e:
            self.logger.error(f"❌ 获取连接池统计失败: {e}")
            return {'error': str(e)}
    
    async def health_check_connections(self) -> Dict[str, Any]:
        """🚀 【新增】检查连接池健康状态"""
        try:
            pool_manager = await self.get_connection_pool_manager()
            if pool_manager:
                return await pool_manager.health_check()
            else:
                return {'overall_status': 'error', 'error': '连接池管理器不可用'}
        except Exception as e:
            self.logger.error(f"❌ 连接池健康检查失败: {e}")
            return {'overall_status': 'error', 'error': str(e)}
    
    def _init_clients(self):
        """初始化各种客户端"""
        try:
            # 网络搜索：优先 DeepSeek Search，保留智谱搜索对象作兼容
            try:
                from utils.deepseek_client import get_deepseek_client

                ds = get_deepseek_client()
                self.search_client = ds if ds.available else zhipu_search
            except Exception:
                self.search_client = zhipu_search

            # 初始化知识库客户端
            self.knowledge_client = KnowledgeBaseClient()

            # 初始化RAG服务 (可选，如果类不存在则跳过)
            try:
                from utils.rag_service import RAGService
                self.rag_service = RAGService(
                    logger=self.logger,
                    search_client=self.search_client,
                    knowledge_client=self.knowledge_client
                )
            except ImportError:
                self.logger.warning("RAG服务不可用，跳过初始化")
                self.rag_service = None

            # 初始化存储管理器
            self.storage_manager = get_storage()

            # 初始化Agent输出存储管理器
            self.output_storage = get_agent_output_storage()
            self.output_archive_service = OutputArchiveService(
                logger=self.logger,
                output_storage=self.output_storage,
                project_manager=self.project_manager,
                agent_id=self.agent_id
            )

            # 初始化LLM客户端
            self._init_llm_client()

            self.logger.info("客户端初始化完成")
        except Exception as e:
            self.logger.error(f"客户端初始化失败: {e}")
            raise
    
    def _init_llm_client(self):
        """初始化LLM客户端"""
        try:
            try:
                from utils.llm_client import get_llm_client
            except ImportError:
                from utils.llm_client import get_llm_client
            
            # 获取基础LLM客户端
            base_llm_client = get_llm_client(self.model_provider)
            
            # 包装LangSmith追踪
            enable_tracing = os.getenv("LANGCHAIN_API_KEY") is not None
            self.llm_client = create_langsmith_llm_client(base_llm_client, enable_tracing)
            
            self.logger.info(f"LLM客户端初始化成功: {self.model_provider}, LangSmith追踪: {'启用' if enable_tracing else '禁用'}")
        except Exception as e:
            self.logger.error(f"LLM客户端初始化失败: {e}")
            # 创建一个模拟的LLM客户端，避免完全失败
            self.llm_client = type('MockLLMClient', (), {
                'chat': lambda self, messages, **kwargs: "模拟响应",
                'stream_chat': lambda self, messages, **kwargs: iter(["模拟", "响应"])
            })()

    def apply_llm_overrides(
        self,
        *,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        """按请求覆盖 LLM 提供商 / 模型 / Key / Base URL（用户自备凭证）。"""
        provider = (provider or "").strip() or self.model_provider
        model = (model or "").strip() or None
        api_key = (api_key or "").strip() or None
        base_url = (base_url or "").strip() or None

        # 无任何覆盖时保持默认客户端
        if (
            provider == self.model_provider
            and not model
            and not api_key
            and not base_url
        ):
            return

        try:
            try:
                from utils.llm_client import get_llm_client
            except ImportError:
                from utils.llm_client import get_llm_client

            kwargs: Dict[str, Any] = {"force_new": True}
            if model:
                kwargs["model"] = model
            if api_key:
                kwargs["api_key"] = api_key
            if base_url:
                kwargs["base_url"] = base_url

            base_llm_client = get_llm_client(provider, **kwargs)
            enable_tracing = os.getenv("LANGCHAIN_API_KEY") is not None
            self.llm_client = create_langsmith_llm_client(base_llm_client, enable_tracing)
            self.model_provider = provider
            self.logger.info(
                f"已应用用户 LLM 覆盖: provider={provider} "
                f"model={model or getattr(base_llm_client, 'model', '?')} "
                f"base_url={'yes' if base_url else 'default'} "
                f"key={'yes' if api_key else 'env'}"
            )
        except Exception as e:
            self.logger.error(f"应用 LLM 覆盖失败: {e}")
            raise
    
    def _load_system_prompt(self):
        """
        加载系统提示词
        🆕 支持风格增强，支持多种加载方式
        """
        try:
            # 1. 优先从Python模块加载
            prompt_module = self._get_prompt_module_name()
            if prompt_module:
                try:
                    module = __import__(f"prompts.{prompt_module}", fromlist=[prompt_module])
                    prompts_dict = getattr(module, f"{prompt_module.upper()}_PROMPTS", {})
                    if self.agent_name in prompts_dict:
                        self.system_prompt = prompts_dict[self.agent_name]
                        self.logger.info(f"从Python模块加载系统提示词成功: {prompt_module}")
                        return
                    elif "main" in prompts_dict:
                        self.system_prompt = prompts_dict["main"]
                        self.logger.info(f"从Python模块加载主提示词成功: {prompt_module}")
                        return
                except (ImportError, AttributeError):
                    pass

            # 2. 从txt文件加载
            prompt_path = Path(__file__).parent.parent / "prompts" / f"{self.agent_name}_system.txt"
            if prompt_path.exists():
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    self.system_prompt = f.read().strip()
                self.logger.info(f"从txt文件加载系统提示词成功: {prompt_path}")
                return

            # 2.5 从JSON/YAML加载
            json_path = Path(__file__).parent.parent / "prompts" / f"{self.agent_name}_system.json"
            yaml_path = Path(__file__).parent.parent / "prompts" / f"{self.agent_name}_system.yaml"
            if json_path.exists():
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.system_prompt = data.get("system_prompt", "").strip()
                if self.system_prompt:
                    self.logger.info(f"从json文件加载系统提示词成功: {json_path}")
                    return
            if yaml_path.exists():
                try:
                    import yaml
                    with open(yaml_path, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                    self.system_prompt = (data or {}).get("system_prompt", "").strip()
                    if self.system_prompt:
                        self.logger.info(f"从yaml文件加载系统提示词成功: {yaml_path}")
                        return
                except Exception:
                    pass

            # 3. 默认提示词
            self.system_prompt = f"你是{self.agent_name}，专业的竖屏短剧策划助手。"
            self.logger.warning(f"使用默认系统提示词: {self.agent_name}")

        except Exception as e:
            self.logger.error(f"加载系统提示词失败: {e}")
            self.system_prompt = f"你是{self.agent_name}，专业的竖屏短剧策划助手。"

    async def enhance_system_prompt_with_style(
        self,
        style: str,
        base_prompt: str = None
    ) -> str:
        """
        🆕 根据风格增强系统提示词

        Args:
            style: 风格标签
            base_prompt: 基础系统提示词（默认使用当前 system_prompt）

        Returns:
            str: 增强后的系统提示词
        """
        base_prompt = base_prompt or self.system_prompt

        # 风格特定的指令映射
        style_instructions = {
            "suspense": """
【风格要求：悬疑/推理】
- 注重营造紧张、神秘的氛围
- 使用伏笔和悬念，逐步揭示真相
- 对话中包含隐含线索，需要读者仔细品味
- 节奏紧凑，制造反转和意外
- 结尾出人意料但合乎逻辑
""",
            "comedy": """
【风格要求：喜剧/搞笑】
- 运用幽默、讽刺、夸张的手法
- 创造尴尬、误会、反转等搞笑情境
- 对话轻松活泼，富有节奏感
- 注重细节描写，通过反差制造笑点
- 结尾温馨或反转，给人轻松愉悦的感觉
""",
            "period": """
【风格要求：古装/历史】
- 使用符合时代背景的语言和称呼
- 注重古典文化元素的融入
- 对话讲究礼仪，体现身份地位
- 场景描写具有古典韵味
- 体现传统价值观和人文情怀
""",
            "modern": """
【风格要求：现代/都市】
- 反映当代都市生活特点和价值观
- 使用贴近生活的对话和场景
- 注重职场、情感、人际关系等现代主题
- 节奏明快，符合现代人的阅读习惯
- 结尾引人深思或温暖治愈
""",
            "romance": """
【风格要求：爱情/浪漫】
- 注重情感细腻的描写
- 对话温柔含蓄或热烈直接
- 营造浪漫氛围和甜蜜互动
- 体现情感的复杂性和成长性
- 结尾圆满或留有遗憾但美好
""",
            "wuxia": """
【风格要求：武侠/江湖】
- 展现武侠世界的豪情与义气
- 使用富有江湖气息的语言
- 动作描写精彩，招式名称有韵味
- 体现武学精神和江湖规矩
- 结尾侠骨柔情，荡气回肠
""",
            "xianxia": """
【风格要求：仙侠/修仙】
- 融入道教文化和修仙理念
- 使用古雅优美的语言
- 法术和境界描写生动形象
- 体现修身养性和天道追求
- 结尾超脱或轮回，意境深远
""",
            "emotional": """
【风格要求：情感/治愈】
- 注重情感深度和内心描写
- 对话真挚感人，触动人心
- 营造温馨治愈的氛围
- 体现亲情、友情、爱情的珍贵
- 结尾温暖美好，给人希望
""",
            "thriller": """
【风格要求：惊悚/悬疑】
- 制造紧张刺激的氛围
- 使用悬念和反转，让人心跳加速
- 对话简洁有力，充满威胁感
- 注重心理恐惧的描写
- 结尾震撼或留有余悸
""",
            "fantasy": """
【风格要求：奇幻/魔法】
- 构建宏大的世界观和魔法体系
- 使用富有想象力的语言和描写
- 法术和魔法效果绚丽多彩
- 体现成长、勇气和友情
- 结尾震撼或留有悬念
""",
            "scifi": """
【风格要求：科幻/未来】
- 融入科技感和未来想象
- 使用科学术语和概念
- 场景描写具有未来感
- 体现人机关系和人性思考
- 结尾发人深省，引发思考
""",
            "horror": """
【风格要求：恐怖/惊悚】
- 营造阴森恐怖的氛围
- 使用感官描写增强代入感
- 节奏张弛有度，制造惊吓点
- 体现人性的阴暗面
- 结尾反转或留下阴影
""",
            "drama": """
【风格要求：剧情/现实】
- 反映现实生活的复杂性和真实性
- 人物刻画丰满立体
- 对话自然流畅，贴近生活
- 情节发展合理，有深度
- 结尾引人深思，发人深省
""",
            "action": """
【风格要求：动作/冒险】
- 动作场面描写精彩刺激
- 打斗场面节奏紧凑，招式连贯
- 环境利用巧妙，制造惊喜
- 体现勇气、智慧和团队精神
- 结尾热血或留有后续
""",
            "historical": """
【风格要求：历史/传记】
- 尊重历史事实和时代背景
- 人物塑造符合历史记载
- 语言风格贴近时代特征
- 体现历史事件的宏大和深远
- 结尾呼应历史，引发思考
""",
            "urban": """
【风格要求：都市/现实】
- 反映都市生活的方方面面
- 人物贴近现实，有代入感
- 场景描写细致真实
- 探讨都市人的情感和价值观
- 结尾温馨或引人深思
""",
            "slapstick": """
【风格要求：滑稽/无厘头】
- 使用夸张、荒诞的手法
- 制造出人意料的情境
- 对话搞笑无厘头
- 注重肢体语言和表情描写
- 结尾反转或延续搞笑
""",
            "youth": """
【风格要求：青春/校园】
- 充满青春活力和朝气
- 语言活泼清新，贴近年轻人口吻
- 场景多为校园或年轻人聚集地
- 探讨友情、爱情、成长等主题
- 结尾美好或充满希望
""",
            "family": """
【风格要求：家庭/亲情】
- 注重家庭成员间的情感
- 语言朴实真挚，有生活气息
- 场景贴近家庭生活
- 体现亲情的温暖和复杂性
- 结尾温馨和谐
""",
        }

        # 获取风格指令
        instruction = style_instructions.get(style, "")

        if instruction:
            enhanced_prompt = f"{base_prompt}\n\n{instruction}"
            self.logger.info(f"✨ 系统提示词已增强风格: {style}")
            return enhanced_prompt

        return base_prompt

    def _get_prompt_module_name(self) -> Optional[str]:
        """根据agent名称获取对应的提示词模块名"""
        # 基于agent名称的模块映射
        module_mapping = {
            "script_evaluation": "script_evaluation_prompts",
            "novel_screening_evaluation": "novel_screening_prompts", 
            "ip_evaluation": "ip_evaluation_prompts",
            "story_evaluation": "novel_screening_prompts",
            "story_outline_evaluation": "story_outline_prompts",
            "drama_analysis": "drama_analysis_prompts",
            "score_analyzer": "story_outline_prompts"
        }
        return module_mapping.get(self.agent_name)
    
    async def _search_web(
        self,
        query: str,
        count: int = 5,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> Dict[str, Any]:
        """
        网络搜索（增强版：带重试、超时和错误处理）

        Args:
            query: 搜索查询
            count: 返回结果数量
            timeout: 超时时间（秒）
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）

        Returns:
            Dict: 搜索结果，格式为 {"success": bool, "results": ..., "error": ...}
        """
        import asyncio

        # ========== 参数验证 ==========
        if not query or not isinstance(query, str):
            return {
                "success": False,
                "error": f"查询参数无效: {query}",
                "results": []
            }

        if count <= 0:
            count = 5
        if timeout <= 0:
            timeout = 30
        if max_retries < 0:
            max_retries = 3

        last_error = None

        for attempt in range(max_retries):
            try:
                self.logger.info(f"开始网络搜索(尝试{attempt + 1}/{max_retries}): {query[:50]}...")

                # 使用asyncio.timeout实现超时控制
                async def do_search():
                    return self.search_client.search_web(query, count=count)

                result = await asyncio.wait_for(do_search(), timeout=timeout)

                # 验证返回结果
                if result is None:
                    raise ValueError("search_web返回None")

                # 获取结果数量
                try:
                    result_count = len(result.get('search_results', {}).get('content', {}).get('search_result', []))
                except Exception:
                    result_count = 0

                self.logger.info(f"网络搜索完成: 获得{result_count}条结果")

                result_payload = {
                    "success": True,
                    "results": result,
                    "result_count": result_count,
                    "error": None
                }
                self._record_rag_trace("web_search", query, result_count)
                return result_payload

            except asyncio.TimeoutError:
                last_error = f"搜索超时({timeout}秒)"
                self.logger.warning(f"{last_error}, 尝试{attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))

            except ValueError as e:
                last_error = f"搜索参数错误: {str(e)}"
                self.logger.error(last_error)
                # 参数错误不重试
                break

            except Exception as e:
                last_error = str(e)
                self.logger.error(f"网络搜索失败(尝试{attempt + 1}/{max_retries}): {e}")

                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))

        # 所有重试都失败
        self.logger.error(f"网络搜索最终失败: {last_error}")
        self._record_rag_trace("web_search", query, 0, error=last_error)
        return {
            "success": False,
            "error": last_error or "搜索失败",
            "results": None
        }

    async def _search_knowledge_base(
        self,
        query: str,
        collection: str = "script_segments",
        top_k: int = 5,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> Dict[str, Any]:
        """
        知识库检索（增强版：带重试、超时和错误处理）

        Args:
            query: 检索查询
            collection: 集合名称
            top_k: 返回结果数量
            timeout: 超时时间（秒）
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）

        Returns:
            Dict: 检索结果，格式为 {"success": bool, "results": ..., "error": ...}
        """
        import asyncio

        # ========== 参数验证 ==========
        if not query or not isinstance(query, str):
            return {
                "success": False,
                "error": f"查询参数无效: {query}",
                "results": []
            }

        if not collection:
            collection = "script_segments"
        if top_k <= 0:
            top_k = 5
        if timeout <= 0:
            timeout = 30
        if max_retries < 0:
            max_retries = 3

        last_error = None

        for attempt in range(max_retries):
            try:
                self.logger.info(f"开始知识库检索(尝试{attempt + 1}/{max_retries}): {query[:50]}..., 集合: {collection}")

                # 使用asyncio.wait_for实现超时控制
                async def do_search():
                    return await self.knowledge_client.search(query, collection=collection, top_k=top_k)

                result = await asyncio.wait_for(do_search(), timeout=timeout)

                # 验证返回结果
                if result is None:
                    raise ValueError("search返回None")

                # 获取结果数量
                result_count = len(result.get('results', [])) if isinstance(result, dict) else 0

                self.logger.info(f"知识库检索完成: 获得{result_count}条结果")

                result_payload = {
                    "success": True,
                    "results": result,
                    "result_count": result_count,
                    "error": None
                }
                self._record_rag_trace("knowledge_base", query, result_count, collection=collection)
                return result_payload

            except asyncio.TimeoutError:
                last_error = f"检索超时({timeout}秒)"
                self.logger.warning(f"{last_error}, 尝试{attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))

            except ValueError as e:
                last_error = f"检索参数错误: {str(e)}"
                self.logger.error(last_error)
                # 参数错误不重试
                break

            except Exception as e:
                last_error = str(e)
                self.logger.error(f"知识库检索失败(尝试{attempt + 1}/{max_retries}): {e}")

                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))

        # 所有重试都失败
        self.logger.error(f"知识库检索最终失败: {last_error}")
        self._record_rag_trace("knowledge_base", query, 0, collection=collection, error=last_error)
        return {
            "success": False,
            "error": last_error or "检索失败",
            "results": None
        }

    def _record_rag_trace(self, source: str, query: str, count: int, **kwargs) -> None:
        try:
            self._rag_trace.append({
                "source": source,
                "query": query,
                "result_count": count,
                "timestamp": datetime.now().isoformat(),
                **kwargs
            })
        except Exception:
            pass

    def get_rag_trace(self) -> List[Dict[str, Any]]:
        return list(self._rag_trace)

    def clear_rag_trace(self) -> None:
        self._rag_trace = []

    def ingest_external_rag_trace(self, rag_trace: Any) -> None:
        """合并外部传入的RAG引用追踪"""
        try:
            if not rag_trace:
                return
            if isinstance(rag_trace, list):
                for item in rag_trace:
                    if isinstance(item, dict):
                        self._rag_trace.append(item)
                    else:
                        self._rag_trace.append({"source": "external", "value": item})
            elif isinstance(rag_trace, dict):
                self._rag_trace.append(rag_trace)
            else:
                self._rag_trace.append({"source": "external", "value": rag_trace})
        except Exception:
            pass
    
    async def _call_llm(self, messages: List[Dict[str, str]], user_id: str = "unknown", session_id: str = "unknown", **kwargs) -> str:
        """调用LLM（增强版：带超时控制）"""
        import asyncio

        try:
            # ========== 参数验证 ==========
            if not messages or not isinstance(messages, list):
                raise ValueError("messages参数不能为空")

            inject_context_pack = kwargs.pop("inject_context_pack", None)
            if inject_context_pack is None:
                inject_context_pack = self.context_pack_enabled and user_id not in ("system", "unknown")

            # 添加系统提示词
            if not any(msg.get("role") == "system" for msg in messages):
                messages.insert(0, {"role": "system", "content": self.system_prompt})

            # 注入输出约束模板
            if self._output_constraint_template and not any(
                isinstance(msg.get("content"), str) and "【输出约束模板】" in msg.get("content", "")
                for msg in messages
            ):
                messages.insert(1, {"role": "system", "content": self._output_constraint_template})

            # 注入上下文包（避免重复注入）
            if inject_context_pack and not any(
                isinstance(msg.get("content"), str) and "【ContextPack】" in msg.get("content", "")
                for msg in messages
            ):
                try:
                    extra = await self._build_context_pack(user_id, session_id, messages[-1].get("content", ""))
                    if extra:
                        messages[1:1] = extra
                except Exception:
                    pass

            # 注入尾部上下文（降低中间遗忘）
            if inject_context_pack and not any(
                isinstance(msg.get("content"), str) and "【ContextTail】" in msg.get("content", "")
                for msg in messages
            ):
                try:
                    tail = await self._build_context_tail(user_id, session_id, messages[-1].get("content", ""))
                    if tail:
                        messages.insert(max(0, len(messages) - 1), tail)
                except Exception:
                    pass

            # 获取超时配置
            timeout = kwargs.pop('timeout', 180)  # 默认180秒超时
            expect_json = kwargs.pop("expect_json", False) or bool(self._output_schema)
            output_schema = kwargs.pop("output_schema", None) or self._output_schema

            # 使用带追踪的LLM调用（带超时）
            async def do_chat():
                if hasattr(self.llm_client, 'chat_with_tracing'):
                    return await self.llm_client.chat_with_tracing(
                        messages=messages,
                        agent_name=self.agent_name,
                        user_id=user_id,
                        session_id=session_id,
                        token_accumulator_key=self.current_token_accumulator_key,
                        **kwargs
                    )
                else:
                    return await self.llm_client.chat(messages, **kwargs)

            # 使用超时控制
            try:
                response = await asyncio.wait_for(do_chat(), timeout=timeout)
            except asyncio.TimeoutError:
                self.logger.error(f"LLM调用超时({timeout}秒)")
                raise TimeoutError(f"LLM调用超时({timeout}秒)")

            # 结构化输出守卫（可选）
            if expect_json or self.structured_output_guard.detect_json_intent(messages):
                if output_schema is None:
                    output_schema = self.structured_output_guard.extract_inline_schema(messages)
                return await self.structured_output_guard.enforce_json_string(
                    self.llm_client,
                    messages,
                    response,
                    schema=output_schema,
                    constraint_template=self._output_constraint_template,
                )

            return response
        except (ValueError, TimeoutError):
            raise
        except Exception as e:
            self.logger.error(f"LLM调用失败: {e}")
            raise

    async def _run_tool_loop(
        self,
        messages: List[Dict[str, Any]],
        *,
        user_id: str = "unknown",
        session_id: str = "unknown",
        drama_id: Optional[str] = None,
        tool_names: Optional[List[str]] = None,
        max_steps: int = 8,
        allow_write: bool = False,
        checkpoint_id: Optional[str] = None,
        on_step: Optional[Callable] = None,
        prompt_cache_extra: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """接入 Agent Infra run_tool_loop（LLM-native tool calling + Deferred Tool Loading）。"""
        from utils.agent_infra.checkpoint import CheckpointStore
        from utils.agent_infra.disclosure import prepare_disclosure
        from utils.agent_infra.runtime import run_tool_loop
        from utils.agent_tools import ToolContext, get_agent_tool_registry, get_tool_harness

        registry = get_agent_tool_registry()
        # 渐进式披露：核心 + tool_search 常驻；其余进名录（若调用方指定 tool_names 则作为 extra_core）
        disclosure = prepare_disclosure(
            registry,
            extra_core=list(tool_names) if tool_names else None,
            include_meta=True,
            include_skills_catalog=True,
            include_agents_catalog=False,
            allow_write=allow_write,
        )
        tools = disclosure.tools
        # 将名录追加进首条 system（若有）
        if disclosure.prompt_append and messages:
            msgs = [dict(m) for m in messages]
            for i, m in enumerate(msgs):
                if m.get("role") == "system":
                    msgs[i] = {
                        **m,
                        "content": (m.get("content") or "") + "\n\n" + disclosure.prompt_append,
                    }
                    break
            else:
                msgs.insert(0, {"role": "system", "content": disclosure.prompt_append})
            messages = msgs

        abort_flag = {"v": False}

        def abort_check() -> bool:
            return abort_flag["v"]

        store = CheckpointStore() if checkpoint_id else None
        return await run_tool_loop(
            client=self.llm_client,
            messages=messages,
            tools=tools,
            harness=get_tool_harness(),
            tool_ctx=ToolContext(
                user_id=user_id,
                session_id=session_id,
                drama_id=drama_id,
                agent_id=self.agent_name,
                allow_write=allow_write,
                metadata={"activated_tools": sorted(disclosure.activated)},
            ),
            max_steps=max_steps,
            checkpoint_store=store,
            checkpoint_id=checkpoint_id or f"{session_id}:{self.agent_name}",
            on_step=on_step,
            abort_check=abort_check,
            prompt_cache_extra=prompt_cache_extra,
        )

    async def _iter_tool_loop(
        self,
        *,
        query: str,
        user_id: str = "unknown",
        session_id: str = "unknown",
        drama_id: Optional[str] = None,
        tool_names: Optional[List[str]] = None,
        max_steps: int = 8,
        allow_write: bool = False,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """带预算上下文的 tool loop，逐步 yield 事件。"""
        from utils.agent_infra.context_budget import assemble_budgeted_prompt
        from utils.agent_infra.prompt_cache import strip_internal_fields

        assembled = await assemble_budgeted_prompt(
            system_prompt=self.system_prompt,
            user_messages=[{"role": "user", "content": query}],
            drama_id=drama_id,
            user_id=user_id,
            query=query,
            session_id=session_id,
            agent_id=self.agent_name,
        )
        messages = strip_internal_fields(assembled.messages)

        queue: List[Dict[str, Any]] = []

        async def on_step(ev: Dict[str, Any]) -> None:
            if ev.get("type") == "tool":
                packed = ev.get("result") or {}
                queue.append(
                    await self._emit_event(
                        "tool_call",
                        packed.get("tool_name") or "",
                        metadata={"parameters": packed.get("parameters"), "tool_call_id": packed.get("tool_call_id")},
                    )
                )
                queue.append(
                    await self._emit_event(
                        "tool_return",
                        packed.get("llm_text") or packed.get("error") or "",
                        metadata={"success": packed.get("success"), "tool_name": packed.get("tool_name")},
                    )
                )

        result = await self._run_tool_loop(
            messages,
            user_id=user_id,
            session_id=session_id,
            drama_id=drama_id,
            tool_names=tool_names,
            max_steps=max_steps,
            allow_write=allow_write,
            on_step=on_step,
            prompt_cache_extra=assembled.extra_body,
        )
        for ev in queue:
            yield ev
        yield await self._emit_event("tool_loop_result", result.to_dict() if hasattr(result, "to_dict") else result)

    async def _call_llm_with_retry(
        self,
        messages: List[Dict[str, str]],
        user_id: str = "unknown",
        session_id: str = "unknown",
        max_retries: int = 3,
        **kwargs
    ) -> str:
        """
        带重试机制的LLM调用

        Args:
            messages: 消息列表
            user_id: 用户ID
            session_id: 会话ID
            max_retries: 最大重试次数 (默认3次)
            **kwargs: 其他参数

        Returns:
            LLM响应字符串

        Raises:
            TimeoutError: 超时错误
            ValueError: 参数错误
            Exception: 其他未处理的异常
        """
        if not TENACITY_AVAILABLE:
            # 如果 tenacity 不可用，直接调用原方法
            self.logger.warning("Tenacity 库不可用，LLM 调用将不使用重试机制")
            return await self._call_llm(messages, user_id, session_id, **kwargs)

        # 定义需要重试的异常类型
        RETRYABLE_EXCEPTIONS = (
            TimeoutError,
            ConnectionError,
            asyncio.TimeoutError,
        )

        # 自定义重试逻辑
        last_exception = None
        for attempt in range(max_retries):
            try:
                return await self._call_llm(messages, user_id, session_id, **kwargs)
            except RETRYABLE_EXCEPTIONS as e:
                last_exception = e
                if attempt < max_retries - 1:
                    # 指数退避: 2^attempt 秒
                    wait_time = 2 ** attempt + random.uniform(0, 1)
                    self.logger.warning(
                        f"LLM 调用失败 (尝试 {attempt + 1}/{max_retries}): {e}，"
                        f"{wait_time:.1f}秒后重试..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(f"LLM 调用失败，已达最大重试次数 {max_retries}")
            except Exception as e:
                # 非可重试异常直接抛出
                self.logger.error(f"LLM 调用遇到不可重试的异常: {e}")
                raise

        # 所有重试都失败后抛出最后的异常
        if last_exception:
            raise last_exception

    async def _stream_llm(self, messages: List[Dict[str, str]], user_id: str = "unknown", session_id: str = "unknown", **kwargs) -> AsyncGenerator[str, None]:
        """流式调用LLM"""
        try:
            expect_json = kwargs.pop("expect_json", False)
            output_schema = kwargs.pop("output_schema", None)
            # 添加系统提示词
            if not any(msg.get("role") == "system" for msg in messages):
                messages.insert(0, {"role": "system", "content": self.system_prompt})

            # 使用带追踪的流式LLM调用
            if hasattr(self.llm_client, 'stream_chat_with_tracing'):
                stream_source = self.llm_client.stream_chat_with_tracing(
                    messages=messages,
                    agent_name=self.agent_name,
                    user_id=user_id,
                    session_id=session_id,
                    token_accumulator_key=self.current_token_accumulator_key,
                    **kwargs
                )
            else:
                stream_source = self.llm_client.stream_chat(messages, **kwargs)

            if expect_json or self.structured_output_guard.detect_json_intent(messages):
                if output_schema is None:
                    output_schema = self.structured_output_guard.extract_inline_schema(messages)
                buffer: List[str] = []
                async for chunk in stream_source:
                    if isinstance(chunk, str) and chunk.startswith("错误:"):
                        yield chunk
                        return
                    if chunk:
                        buffer.append(chunk)
                full_output = "".join(buffer)
                guarded = await self.structured_output_guard.enforce_json_string(
                    self.llm_client,
                    messages,
                    full_output,
                    schema=output_schema,
                )
                yield guarded
                return

            async for chunk in stream_source:
                yield chunk
        except Exception as e:
            self.logger.error(f"LLM流式调用失败: {e}")
            yield f"错误: {str(e)}"

    async def _stream_llm_with_separation(
        self,
        messages: List[Dict[str, str]],
        user_id: str = "unknown",
        session_id: str = "unknown",
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式调用LLM（增强版：推理内容与正文内容分离）

        自动识别并分离推理过程（thinking/reasoning）和正文内容，
        通过不同的事件类型返回。

        支持的思考标签格式：
        - <think>...</think>
        - <thinking>...</thinking>
        - <reasoning>...</reasoning>
        - <thought>...</thought>

        Yields:
            Dict: 包含以下键的字典
                - event_type: "thinking", "content", "thinking_complete", "error"
                - data: 内容片段
                - metadata: 额外元数据
        """
        try:
            expect_json = kwargs.pop("expect_json", False)
            output_schema = kwargs.pop("output_schema", None)
            # 添加系统提示词
            if not any(msg.get("role") == "system" for msg in messages):
                messages.insert(0, {"role": "system", "content": self.system_prompt})

            # 思考标签模式
            thinking_patterns = {
                '<think>': '</think>',
                '<thinking>': '</thinking>',
                '<reasoning>': '</reasoning>',
                '<thought>': '</thought>',
            }

            # 状态机
            in_thinking = False
            current_thinking_tag = None
            thinking_buffer = []
            content_buffer = []

            # 获取流式内容源
            if hasattr(self.llm_client, 'stream_chat_with_tracing'):
                stream_source = self.llm_client.stream_chat_with_tracing(
                    messages=messages,
                    agent_name=self.agent_name,
                    user_id=user_id,
                    session_id=session_id,
                    token_accumulator_key=self.current_token_accumulator_key,
                    **kwargs
                )
            else:
                stream_source = self.llm_client.stream_chat(messages, **kwargs)

            if expect_json or self.structured_output_guard.detect_json_intent(messages):
                if output_schema is None:
                    output_schema = self.structured_output_guard.extract_inline_schema(messages)
                buffer: List[str] = []
                async for chunk in stream_source:
                    if isinstance(chunk, str) and chunk.startswith("错误:"):
                        yield {"event_type": "error", "data": chunk, "metadata": {}}
                        return
                    if chunk:
                        buffer.append(chunk)
                full_output = "".join(buffer)
                guarded = await self.structured_output_guard.enforce_json_string(
                    self.llm_client,
                    messages,
                    full_output,
                    schema=output_schema,
                )
                yield {"event_type": "content", "data": guarded, "metadata": {"schema_guarded": True}}
                yield {"event_type": "stream_complete", "data": "", "metadata": {}}
                return

            async for chunk in stream_source:
                if not chunk:
                    continue

                # 检查错误
                if isinstance(chunk, str) and chunk.startswith("错误:"):
                    yield {
                        "event_type": "error",
                        "data": chunk,
                        "metadata": {}
                    }
                    break

                # 处理内容，检测思考标签
                remaining = chunk

                while remaining:
                    if in_thinking:
                        # 检查是否到达思考结束标签
                        end_tag = current_thinking_tag
                        end_pos = remaining.find(end_tag)

                        if end_pos >= 0:
                            # 找到结束标签
                            thinking_content = remaining[:end_pos]
                            thinking_buffer.append(thinking_content)

                            # 发送思考完成事件
                            complete_thinking = "".join(thinking_buffer)
                            if self.should_emit_thought(complete_thinking):
                                yield {
                                    "event_type": "thinking_complete",
                                    "data": complete_thinking,
                                    "metadata": {"tag": current_thinking_tag}
                                }

                            # 重置状态
                            thinking_buffer = []
                            in_thinking = False
                            current_thinking_tag = None

                            # 处理剩余内容
                            remaining = remaining[end_pos + len(end_tag):]
                        else:
                            # 整个chunk都是思考内容
                            thinking_buffer.append(remaining)
                            # 发送思考片段
                            if self.should_emit_thought("".join(thinking_buffer)):
                                yield {
                                    "event_type": "thinking",
                                    "data": remaining,
                                    "metadata": {"tag": current_thinking_tag or "unknown"}
                                }
                            remaining = ""
                    else:
                        # 不在思考中，检查是否有开始标签
                        found_tag = False
                        for start_tag, end_tag in thinking_patterns.items():
                            tag_pos = remaining.find(start_tag)
                            if tag_pos >= 0:
                                # 找到开始标签
                                # 先处理标签前的内容作为正文
                                before_tag = remaining[:tag_pos]
                                if before_tag:
                                    content_buffer.append(before_tag)
                                    yield {
                                        "event_type": "content",
                                        "data": before_tag,
                                        "metadata": {}
                                    }

                                # 进入思考状态
                                in_thinking = True
                                current_thinking_tag = end_tag
                                remaining = remaining[tag_pos + len(start_tag):]
                                found_tag = True
                                break

                        if not found_tag:
                            # 没有找到标签，整个chunk作为正文
                            content_buffer.append(remaining)
                            yield {
                                "event_type": "content",
                                "data": remaining,
                                "metadata": {}
                            }
                            remaining = ""

            # 处理未关闭的思考标签
            if in_thinking and thinking_buffer:
                self.logger.warning(f"检测到未关闭的思考标签，将剩余内容作为正文处理")
                complete_thinking = "".join(thinking_buffer)
                # 将未完成的思考作为正文返回
                yield {
                    "event_type": "content",
                    "data": complete_thinking,
                    "metadata": {"note": "未关闭的思考标签已作为正文处理"}
                }

            # 发送流式完成标记
            yield {
                "event_type": "stream_complete",
                "data": "",
                "metadata": {}
            }

        except Exception as e:
            self.logger.error(f"LLM流式调用失败: {e}")
            yield {
                "event_type": "error",
                "data": str(e),
                "metadata": {"error_type": type(e).__name__}
            }
    
    def _build_user_prompt(self, request_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        """构建用户提示词"""
        try:
            query = request_data.get("input", "")
            user_id = context.get("user_id", "unknown") if context else "unknown"
            session_id = context.get("session_id", "unknown") if context else "unknown"
            
            # 基础提示词
            base_prompt = f"用户查询: {query}\n"
            
            # 添加上下文信息
            if context:
                if context.get("search_results"):
                    base_prompt += f"\n搜索结果: {json.dumps(context['search_results'], ensure_ascii=False, indent=2)}\n"
                
                if context.get("knowledge_results"):
                    base_prompt += f"\n知识库结果: {json.dumps(context['knowledge_results'], ensure_ascii=False, indent=2)}\n"
            
            return base_prompt
        except Exception as e:
            self.logger.warning(f"构建用户提示词失败: {e}")
            return f"用户查询: {request_data.get('input', '')}"
    
    async def _emit_event(self, event_type: str, data: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """发送事件"""
        event = {
            "event_type": event_type,
            "agent_source": self.agent_name,
            "timestamp": datetime.now().isoformat(),
            "data": data,
            "metadata": metadata or {}
        }
        return event
    
    # ==================== Token统计方法 ====================
    
    async def initialize_token_accumulator(self, user_id: str, session_id: str, request_timestamp: Optional[str] = None) -> str:
        """
        初始化Token累加器（会话级别）
        
        Args:
            user_id: 用户ID
            session_id: 会话ID
            request_timestamp: 请求时间戳（已弃用，保留是为了兼容性）
            
        Returns:
            str: 累加器键
        """
        try:
            accumulator_key = create_token_accumulator(user_id, session_id, request_timestamp)
            self.current_token_accumulator_key = accumulator_key
            self.logger.info(f"🔢 {self.agent_name} 创建Token累加器: {accumulator_key}")
            return accumulator_key
        except Exception as e:
            self.logger.error(f"❌ 初始化Token累加器失败: {e}")
            return None
    
    async def get_token_billing_summary(self) -> Optional[Dict[str, Any]]:
        """
        获取Token计费摘要
        
        Returns:
            Dict: 计费摘要
        """
        if not self.current_token_accumulator_key:
            self.logger.warning("⚠️ 没有活跃的Token累加器")
            return None
        
        try:
            summary = get_billing_summary(self.current_token_accumulator_key)
            if summary:
                self.logger.info(f"📊 Token计费摘要: {summary['total_tokens']} tokens, {summary['deducted_points']} 积分")
            return summary
        except Exception as e:
            self.logger.error(f"❌ 获取Token计费摘要失败: {e}")
            return None
    
    def set_token_accumulator(self, accumulator_key: str):
        """
        设置Token累加器键
        
        Args:
            accumulator_key: 累加器键
        """
        self.current_token_accumulator_key = accumulator_key
        self.logger.info(f"🔢 {self.agent_name} 设置Token累加器: {accumulator_key}")
    
    # ==================== 数据存储方法 ====================
    
    async def save_chat_message(self, user_id: str, session_id: str, message_type: str, 
                               content: str, metadata: Dict[str, Any] = None) -> Optional[str]:
        """保存聊天消息"""
        try:
            message = ChatMessage(
                user_id=user_id,
                session_id=session_id,
                message_type=message_type,
                content=content,
                agent_name=self.agent_name,
                message_metadata=metadata or {}
            )
            
            message_id = await self.storage_manager.save_chat_message(message)
            if message_id:
                self.logger.info(f"💾 {self.agent_name} 保存聊天消息成功: {message_id}")
            return message_id
            
        except Exception as e:
            self.logger.error(f"❌ 保存聊天消息失败: {e}")
            return None
    
    async def get_chat_messages(self, user_id: str, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取聊天消息"""
        try:
            messages = await self.storage_manager.get_chat_messages(user_id, session_id, limit)
            return messages
        except Exception as e:
            self.logger.error(f"❌ 获取聊天消息失败: {e}")
            return []

    # ==================== Notes系统 - Agent输出自动保存 ====================

    # Agent名称到Note内容类型的映射
    _AGENT_CONTENT_TYPE_MAPPING = {
        'character_profile_generator': 'character_profile',
        'character_relationship_analyzer': 'character_relationship',
        'plot_points_analyzer': 'plot_point',
        'story_summary_generator': 'story_outline',
        'major_plot_points_agent': 'major_plot',
        'detailed_plot_points_agent': 'detailed_plot',
        'script_evaluation_agent': 'script_evaluation',
        'ip_evaluation_agent': 'ip_evaluation',
        'ip_evaluation': 'ip_evaluation',
        'story_evaluation_agent': 'evaluation',
        'story_outline_evaluation_agent': 'evaluation',
        'short_drama_evaluation_agent': 'evaluation',
        'short_drama_evaluation': 'evaluation',
        'novel_screening_evaluation_agent': 'evaluation',
        'short_drama_creator_agent': 'script',
        'short_drama_creator': 'script',
        'short_drama_planner_agent': 'drama_plan',
        'short_drama_planner': 'drama_plan',
        'drama_analysis_agent': 'drama_analysis',
        'mind_map_agent': 'mind_map',
        'document_generator_agent': 'script',
        'story_five_elements_agent': 'story_outline',
        'story_five_elements': 'story_outline',
        'plot_points_workflow_agent': 'plot_point',
        'plot_points_workflow': 'plot_point',
    }

    # Agent名称到Note标题前缀的映射
    _AGENT_TITLE_PREFIX_MAPPING = {
        'character_profile_generator': '人物小传',
        'character_relationship_analyzer': '人物关系',
        'plot_points_analyzer': '情节点分析',
        'story_summary_generator': '故事大纲',
        'major_plot_points_agent': '大情节点',
        'detailed_plot_points_agent': '详细情节点',
        'script_evaluation_agent': '剧本评估',
        'ip_evaluation_agent': 'IP评估',
        'ip_evaluation': 'IP评估',
        'story_evaluation_agent': '故事评估',
        'story_outline_evaluation_agent': '大纲评估',
        'short_drama_evaluation_agent': '短剧评估',
        'short_drama_evaluation': '短剧评估',
        'novel_screening_evaluation_agent': '小说筛选评估',
        'short_drama_creator_agent': '短剧剧本',
        'short_drama_creator': '短剧剧本',
        'short_drama_planner_agent': '短剧策划',
        'short_drama_planner': '短剧策划',
        'drama_analysis_agent': '拉片分析',
        'mind_map_agent': '思维导图',
        'document_generator_agent': '文档生成',
        'story_five_elements_agent': '故事五元素',
        'story_five_elements': '故事五元素',
        'plot_points_workflow_agent': '情节点工作流',
        'plot_points_workflow': '情节点工作流',
    }

    _OUTPUT_TAG_PHASE_MAPPING = OUTPUT_TAG_PHASE_MAPPING
    _AGENT_CATEGORY_MAPPING = AGENT_CATEGORY_MAPPING

    async def save_agent_output_as_note(
        self,
        user_id: str,
        session_id: str,
        output_content: str,
        name: Optional[str] = None,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        保存Agent输出为Note

        Args:
            user_id: 用户ID
            session_id: 会话ID
            output_content: 输出内容
            name: Note名称（唯一标识），如果不提供则自动生成
            title: Note标题，如果不提供则使用默认格式
            metadata: 额外元数据

        Returns:
            str: Note ID，失败返回None
        """
        try:
            # 获取action类型
            action = self.agent_name

            # 生成Note名称（如果不提供）
            if not name:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                name = f"{action}_{timestamp}"

            # 生成Note标题（如果不提供）
            if not title:
                title_prefix = self._AGENT_TITLE_PREFIX_MAPPING.get(action, action)
                title = f"{title_prefix} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

            # 构建元数据
            note_metadata = {
                'agent_name': self.agent_id,
                'content_type': self._AGENT_CONTENT_TYPE_MAPPING.get(action, 'insight'),
                'generated_at': datetime.now().isoformat(),
                'output_tag': self._determine_output_tag(self.agent_id),
                'category': self._AGENT_CATEGORY_MAPPING.get(self.agent_id, 'utility'),
                'phase': self._OUTPUT_TAG_PHASE_MAPPING.get(self._determine_output_tag(self.agent_id), 'utility'),
            }
            rag_trace = self.get_rag_trace()
            if rag_trace:
                note_metadata["rag_trace"] = rag_trace
            if metadata:
                note_metadata.update(metadata)

            # 调用storage_manager保存
            storage = await get_storage()
            note_id = await storage.save_agent_output_note(
                user_id=user_id,
                session_id=session_id,
                action=action,
                name=name,
                context=output_content,
                title=title,
                metadata=note_metadata,
                select_status=0  # 默认未选择
            )

            if note_id:
                self.logger.info(f"📝 {self.agent_name} 保存Agent输出为Note成功: {note_id}")
            self.clear_rag_trace()
            return note_id

        except Exception as e:
            self.logger.error(f"❌ 保存Agent输出为Note失败: {e}")
            return None

    async def _collect_and_save_output(
        self,
        user_id: str,
        session_id: str,
        event_generator: AsyncGenerator[Dict[str, Any], None],
        auto_save_note: bool = True,
        note_name: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        收集流式输出并自动保存为Note

        Args:
            user_id: 用户ID
            session_id: 会话ID
            event_generator: 事件生成器
            auto_save_note: 是否自动保存为Note
            note_name: Note名称（可选）

        Yields:
            Dict: 流式响应事件
        """
        output_buffer = []

        try:
            async for event in event_generator:
                yield event

                # 收集文本内容
                event_type = event.get('event_type', '')
                if event_type == 'llm_chunk':
                    # LLM流式输出
                    data = event.get('data', '')
                    if isinstance(data, str):
                        output_buffer.append(data)
                elif event_type in ['analysis_result', 'generation_result', 'result',
                                    'final_result', 'integrated_result', 'workflow_result']:
                    # 完整结果事件
                    if isinstance(event.get('data'), dict):
                        # 提取结果内容
                        for key in ['analysis', 'result', 'final_result', 'integrated_result', 'content', 'output']:
                            if key in event['data']:
                                content = event['data'][key]
                                if isinstance(content, str) and content:
                                    output_buffer = [content]  # 替换为完整结果
                                    break
                    elif isinstance(event.get('data'), str):
                        output_buffer = [event['data']]

                # 当收到完成事件时，保存Note
                if auto_save_note and event_type in ['done', 'complete', 'workflow_complete']:
                    full_output = ''.join(output_buffer)
                    if full_output and len(full_output.strip()) > 10:
                        await self.save_agent_output_as_note(
                            user_id=user_id,
                            session_id=session_id,
                            output_content=full_output,
                            name=note_name
                        )

        except Exception as e:
            self.logger.error(f"❌ 收集和保存输出失败: {e}")
            # 即使出错也要yield事件
            yield await self._emit_event("error", f"保存输出失败: {str(e)}")

    async def get_chat_messages(self, user_id: str, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取聊天消息"""
        try:
            messages = await self.storage_manager.get_chat_messages(user_id, session_id, limit)
            self.logger.info(f"📖 {self.agent_name} 获取聊天消息: {len(messages)}条")
            return messages
        except Exception as e:
            self.logger.error(f"❌ 获取聊天消息失败: {e}")
            return []

    async def save_context_state(self, user_id: str, session_id: str, context_data: Dict[str, Any]) -> bool:
        """保存上下文状态"""
        try:
            context = ContextState(
                user_id=user_id,
                session_id=session_id,
                agent_name=self.agent_name,
                context_data=context_data
            )
            
            success = await self.storage_manager.save_context_state(context)
            if success:
                self.logger.info(f"💾 {self.agent_name} 保存上下文状态成功")
            return success
            
        except Exception as e:
            self.logger.error(f"❌ 保存上下文状态失败: {e}")
            return False
    
    async def get_context_state(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """获取上下文状态"""
        try:
            context_data = await self.storage_manager.get_context_state(user_id, session_id, self.agent_name)
            if context_data:
                self.logger.info(f"📖 {self.agent_name} 获取上下文状态成功")
            return context_data
        except Exception as e:
            self.logger.error(f"❌ 获取上下文状态失败: {e}")
            return None
    
    async def save_note(self, user_id: str, session_id: str, action: str, name: str, 
                       context: str, title: Optional[str] = None, select_status: int = 0,
                       metadata: Dict[str, Any] = None) -> Optional[str]:
        """保存Note"""
        try:
            note = Note(
                user_id=user_id,
                session_id=session_id,
                action=action,
                name=name,
                title=title,
                context=context,
                select_status=select_status,
                metadata=metadata or {}
            )
            
            note_id = await self.storage_manager.save_note(note)
            if note_id:
                self.logger.info(f"💾 {self.agent_name} 保存Note成功: {note_id}")
            return note_id
            
        except Exception as e:
            self.logger.error(f"❌ 保存Note失败: {e}")
            return None
    
    async def get_notes(self, user_id: str, session_id: str, action: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取Notes"""
        try:
            notes = await self.storage_manager.get_notes(user_id, session_id, action)
            self.logger.info(f"📖 {self.agent_name} 获取Notes: {len(notes)}条")
            return notes
        except Exception as e:
            self.logger.error(f"❌ 获取Notes失败: {e}")
            return []
    
    async def save_token_usage(self, user_id: str, session_id: str, model_provider: str, 
                              model_name: str, request_tokens: int, response_tokens: int,
                              cost_points: float, billing_summary: Dict[str, Any] = None) -> Optional[str]:
        """保存Token使用记录"""
        try:
            token_usage = TokenUsage(
                user_id=user_id,
                session_id=session_id,
                agent_name=self.agent_name,
                model_provider=model_provider,
                model_name=model_name,
                request_tokens=request_tokens,
                response_tokens=response_tokens,
                total_tokens=request_tokens + response_tokens,
                cost_points=cost_points,
                billing_summary=billing_summary or {}
            )
            
            usage_id = await self.storage_manager.save_token_usage(token_usage)
            if usage_id:
                self.logger.info(f"💾 {self.agent_name} 保存Token使用记录成功: {usage_id}")
            return usage_id
            
        except Exception as e:
            self.logger.error(f"❌ 保存Token使用记录失败: {e}")
            return None
    
    async def save_stream_event(self, user_id: str, session_id: str, event_type: str,
                               content_type: Optional[str], event_data: Any, 
                               event_metadata: Dict[str, Any] = None) -> Optional[str]:
        """保存流式事件"""
        try:
            event_id = await self.storage_manager.save_stream_event(
                user_id=user_id,
                session_id=session_id,
                event_type=event_type,
                content_type=content_type,
                agent_source=self.agent_name,
                event_data=event_data,
                event_metadata=event_metadata or {}
            )
            
            if event_id:
                self.logger.info(f"💾 {self.agent_name} 保存流式事件成功: {event_id}")
            return event_id
            
        except Exception as e:
            self.logger.error(f"❌ 保存流式事件失败: {e}")
            return None
    
    async def create_user_session(self, user_id: str, session_id: str, metadata: Dict[str, Any] = None) -> bool:
        """创建用户会话"""
        try:
            success = await self.storage_manager.create_user_session(user_id, session_id, metadata)
            if success:
                self.logger.info(f"💾 {self.agent_name} 创建用户会话成功: {user_id}:{session_id}")
            return success
        except Exception as e:
            self.logger.error(f"❌ 创建用户会话失败: {e}")
            return False
    
    async def update_session_activity(self, user_id: str, session_id: str) -> bool:
        """更新会话活动时间"""
        try:
            success = await self.storage_manager.update_session_activity(user_id, session_id)
            return success
        except Exception as e:
            self.logger.error(f"❌ 更新会话活动时间失败: {e}")
            return False
    
    # ==================== Agent输出存储方法 ====================
    
    async def save_agent_output(
        self,
        output_content: Union[str, Dict[str, Any]],
        output_tag: str,
        user_id: str,
        session_id: str,
        file_type: str = "json",
        metadata: Optional[Dict[str, Any]] = None,
        auto_export: bool = True
    ) -> Dict[str, Any]:
        """
        保存Agent输出内容到文件系统
        🆕 增强版：同时保存到项目文件系统

        Args:
            output_content: 输出内容
            output_tag: 输出标签（drama_planning, drama_creation, drama_evaluation, novel_screening等）
            user_id: 用户ID
            session_id: 会话ID
            file_type: 文件类型（json, markdown, text, html, xml）
            metadata: 元数据
            auto_export: 是否自动导出

        Returns:
            Dict: 保存结果信息
        """
        try:
            # 聚合RAG证据链
            rag_trace = self.get_rag_trace()
            merged_metadata = metadata.copy() if metadata else {}
            if rag_trace:
                merged_metadata["rag_trace"] = rag_trace

            # 原有的保存逻辑
            result = await self.output_storage.save_agent_output(
                agent_name=self.agent_id,
                output_content=output_content,
                output_tag=output_tag,
                user_id=user_id,
                session_id=session_id,
                file_type=file_type,
                metadata=merged_metadata,
                auto_export=auto_export
            )

            if result.get("success"):
                self.logger.info(f"💾 {self.agent_name} 输出保存成功: {output_tag}")

                # 🆕 【新增】同时保存到项目文件系统
                if self.project_manager:
                    await self._save_to_project_filesystem(
                        output_content=output_content,
                        output_tag=output_tag,
                        user_id=user_id,
                        session_id=session_id,
                        metadata=merged_metadata
                    )
                # 🆕 同步归档到 Artifacts
                if self.output_archive_service:
                    await self.output_archive_service.save_all(
                        output_content=output_content,
                        output_tag=output_tag,
                        user_id=user_id,
                        session_id=session_id,
                        metadata=merged_metadata
                    )
            else:
                self.logger.error(f"❌ {self.agent_name} 输出保存失败: {result.get('error')}")

            self.clear_rag_trace()
            return result

        except Exception as e:
            self.logger.error(f"❌ 保存Agent输出失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_agent_outputs(
        self, 
        output_tag: str, 
        user_id: Optional[str] = None, 
        session_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取Agent输出列表"""
        try:
            outputs = await self.output_storage.get_agent_outputs(
                output_tag=output_tag,
                user_id=user_id,
                session_id=session_id,
                agent_name=self.agent_name,
                limit=limit
            )
            
            self.logger.info(f"📖 {self.agent_name} 获取输出列表: {len(outputs)}条")
            return outputs
            
        except Exception as e:
            self.logger.error(f"❌ 获取Agent输出列表失败: {e}")
            return []
    
    async def get_output_content(
        self, 
        file_id: str, 
        output_tag: str
    ) -> Optional[Dict[str, Any]]:
        """获取输出内容"""
        try:
            content = await self.output_storage.get_output_content(file_id, output_tag)
            if content:
                self.logger.info(f"📖 {self.agent_name} 获取输出内容成功: {file_id}")
            return content
            
        except Exception as e:
            self.logger.error(f"❌ 获取输出内容失败: {e}")
            return None
    
    def _determine_output_tag(self, agent_name: str) -> str:
        """根据Agent名称确定输出标签"""
        # 基于Agent名称的标签映射
        agent_tag_mapping = {
            # 短剧策划相关
            "juben_orchestrator": "drama_planning",
            "juben_concierge": "drama_planning", 
            "short_drama_planner_agent": "drama_planning",
            "short_drama_planner": "drama_planning",
            
            # 短剧创作相关
            "short_drama_creator_agent": "drama_creation",
            "short_drama_creator": "drama_creation",
            "story_outline_evaluation_agent": "drama_creation",
            "character_profile_agent": "drama_creation",
            "character_profile_generator_agent": "drama_creation",
            "character_relationship_agent": "drama_creation",
            "character_relationship_analyzer_agent": "drama_creation",
            
            # 短剧评估相关
            "short_drama_evaluation_agent": "drama_evaluation",
            "short_drama_evaluation": "drama_evaluation",
            "script_evaluation_agent": "drama_evaluation",
            "drama_analysis_agent": "drama_evaluation",
            "drama_workflow_agent": "drama_evaluation",
            "script_evaluation_orchestrator": "drama_evaluation",
            
            # 小说初筛评估相关
            "novel_screening_evaluation_agent": "novel_screening",
            "ip_evaluation_agent": "novel_screening",
            "ip_evaluation": "novel_screening",
            "ip_evaluation_orchestrator": "novel_screening",
            
            # 故事分析相关
            "story_five_elements_agent": "story_analysis",
            "story_five_elements": "story_analysis",
            "story_five_elements_orchestrator": "story_analysis",
            "story_evaluation_agent": "story_analysis",
            "story_summary_agent": "story_analysis",
            "story_summary_generator_agent": "story_analysis",
            "story_synopsis_agent": "story_analysis",
            "story_type_analyzer_agent": "story_analysis",
            
            # 角色开发相关
            "character_profile_agent": "character_development",
            "character_relationship_agent": "character_development",
            "character_relationship_analyzer_agent": "character_development",
            
            # 情节开发相关
            "plot_points_agent": "plot_development",
            "major_plot_points_agent": "plot_development",
            "detailed_plot_points_agent": "plot_development",
            "plot_points_analyzer_agent": "plot_development",
            "plot_points_drama_analysis_agent": "plot_development",
            "plot_points_workflow_agent": "plot_development",
            "plot_points_workflow": "plot_development",
            
            # 剧集分析相关
            "series_analysis_agent": "series_analysis",
            "series_analysis_orchestrator": "series_analysis",
            "series_info_agent": "series_analysis",
            "series_name_extractor_agent": "series_analysis"
        }
        
        return agent_tag_mapping.get(agent_name, "drama_planning")  # 默认标签
    
    async def auto_save_output(
        self, 
        output_content: Union[str, Dict[str, Any]], 
        user_id: str, 
        session_id: str, 
        file_type: str = "json",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        自动保存Agent输出（根据Agent名称自动确定标签）
        
        Args:
            output_content: 输出内容
            user_id: 用户ID
            session_id: 会话ID
            file_type: 文件类型
            metadata: 元数据
            
        Returns:
            Dict: 保存结果信息
        """
        try:
            # 自动确定输出标签
            output_tag = self._determine_output_tag(self.agent_name)
            
            # 保存输出
            result = await self.save_agent_output(
                output_content=output_content,
                output_tag=output_tag,
                user_id=user_id,
                session_id=session_id,
                file_type=file_type,
                metadata=metadata,
                auto_export=True
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 自动保存输出失败: {e}")
            return {"success": False, "error": str(e)}

    # ==================== 项目文件系统集成方法（新增）====================

    async def _save_to_project_filesystem(
        self,
        output_content: Union[str, Dict[str, Any]],
        output_tag: str,
        user_id: str,
        session_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        🆕 保存Agent输出到项目文件系统

        Args:
            output_content: 输出内容
            output_tag: 输出标签
            user_id: 用户ID
            session_id: 会话ID
            metadata: 元数据

        Returns:
            bool: 是否保存成功
        """
        try:
            # 获取或创建项目
            project = await self.get_or_create_project(user_id, session_id)
            if not project:
                self.logger.warning(f"⚠️ 无法获取或创建项目: {user_id}/{session_id}")
                return False

            # 映射输出标签到文件类型
            file_type = self._map_output_tag_to_file_type(output_tag)

            # 生成文件名
            filename = self._generate_project_filename(output_tag)

            # 提取标签
            tags = self._extract_tags_from_output(output_tag, metadata)

            # 添加文件到项目
            project_file = await self.project_manager.add_file_to_project(
                project_id=project.id,
                filename=filename,
                file_type=file_type,
                content=output_content,
                agent_source=self.agent_id,
                tags=tags
            )

            if project_file:
                self.logger.info(f"💾 项目文件已保存: {project.name}/{filename}")
                try:
                    phase = self._OUTPUT_TAG_PHASE_MAPPING.get(output_tag, "utility")
                    category = self._AGENT_CATEGORY_MAPPING.get(self.agent_id, "utility")
                    merged_tags = set(project.tags or [])
                    merged_tags.update([
                        f"phase:{phase}",
                        f"category:{category}",
                        f"agent:{self.agent_id}",
                        f"output:{output_tag}",
                    ])
                    await self.project_manager.update_project(
                        project_id=project.id,
                        tags=sorted(merged_tags)
                    )
                except Exception as tag_error:
                    self.logger.warning(f"⚠️ 更新项目标签失败: {tag_error}")
                return True
            else:
                self.logger.warning(f"⚠️ 项目文件保存失败: {filename}")
                return False

        except Exception as e:
            self.logger.error(f"❌ 保存到项目文件系统失败: {e}")
            return False

    def _map_output_tag_to_file_type(self, output_tag: str) -> FileType:
        """
        🆕 映射输出标签到文件类型

        Args:
            output_tag: 输出标签

        Returns:
            FileType: 文件类型
        """
        # 输出标签到文件类型的映射
        tag_to_type = {
            "drama_planning": FileType.DRAMA_PLANNING,
            "drama_creation": FileType.SCRIPT,
            "drama_evaluation": FileType.EVALUATION,
            "novel_screening": FileType.EVALUATION,
            "story_analysis": FileType.EVALUATION,
            "character_development": FileType.CHARACTER_PROFILE,
            "plot_development": FileType.PLOT_POINTS,
            "series_analysis": FileType.EVALUATION,
            "conversation": FileType.CONVERSATION,
            "note": FileType.NOTE,
            "reference": FileType.REFERENCE,
        }

        return tag_to_type.get(output_tag, FileType.OTHER)

    def _generate_project_filename(self, output_tag: str) -> str:
        """
        🆕 生成项目文件名

        Args:
            output_tag: 输出标签

        Returns:
            str: 文件名
        """
        # 使用时间戳和agent名称生成唯一文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{output_tag}_{self.agent_name}_{timestamp}"

    def _extract_tags_from_output(
        self,
        output_tag: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        🆕 从输出中提取标签

        Args:
            output_tag: 输出标签
            metadata: 元数据

        Returns:
            List[str]: 标签列表
        """
        phase = self._OUTPUT_TAG_PHASE_MAPPING.get(output_tag, "utility")
        category = self._AGENT_CATEGORY_MAPPING.get(self.agent_id, "utility")
        tags = [
            output_tag,
            self.agent_id,
            f"phase:{phase}",
            f"category:{category}",
            f"agent:{self.agent_id}",
            f"output:{output_tag}",
        ]

        # 从元数据中提取标签
        if metadata:
            if "tags" in metadata:
                tags.extend(metadata["tags"])
            if "category" in metadata:
                tags.append(metadata["category"])

        return list(dict.fromkeys(tags))

    async def get_or_create_project(
        self,
        user_id: str,
        session_id: str,
        project_name: str = None
    ) -> Optional[Any]:
        """
        🆕 获取或创建会话对应的项目

        Args:
            user_id: 用户ID
            session_id: 会话ID
            project_name: 项目名称（如果为None，则尝试从上下文获取）

        Returns:
            Project: 项目对象，如果失败返回None
        """
        try:
            if not self.project_manager:
                return None

            # 尝试从现有项目中查找（通过会话ID在元数据中查找）
            projects = await self.project_manager.list_projects(user_id=user_id)

            # 查找匹配session_id的项目
            for project in projects:
                if project.metadata.get("session_id") == session_id:
                    return project

            # 如果没有找到，创建新项目
            if not project_name:
                # 尝试从对话历史中获取初始查询作为项目名称
                project_name = await self._get_project_name_from_context(user_id, session_id)

                # 如果仍然没有，使用默认名称
                if not project_name:
                    project_name = f"项目_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # 创建新项目
            project = await self.project_manager.create_project(
                name=project_name,
                user_id=user_id,
                description=f"会话 {session_id} 的项目",
                tags=["auto_created"],
                metadata={"session_id": session_id, "agent_name": self.agent_name}
            )

            self.logger.info(f"✅ 创建新项目: {project.name} ({project.id})")
            return project

        except Exception as e:
            self.logger.error(f"❌ 获取或创建项目失败: {e}")
            return None

    async def _get_project_name_from_context(self, user_id: str, session_id: str) -> Optional[str]:
        """
        🆕 从上下文获取项目名称

        Args:
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            Optional[str]: 项目名称
        """
        try:
            # 获取对话历史
            messages = await self.get_chat_messages(user_id, session_id, limit=10)

            # 查找第一条用户消息作为项目名称
            for msg in messages:
                if msg.get("message_type") == "user":
                    content = msg.get("content", "")
                    # 截取前30个字符作为项目名称
                    project_name = content[:30] + "..." if len(content) > 30 else content
                    return project_name

            return None

        except Exception as e:
            self.logger.warning(f"⚠️ 从上下文获取项目名称失败: {e}")
            return None

    @abstractmethod
    async def process_request(
        self,
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """处理请求的抽象方法，子类必须实现"""
        pass

    async def process_request_with_enhanced_context(
        self,
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        enable_rag: bool = False,
        enable_smart_select: bool = False,
        context_sources: Optional[List[str]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理请求（带增强上下文管理）

        这是process_request的增强版本，自动启用：
        - RAG自动加载
        - 智能上下文选择
        - 消息与内部笔记隔离
        - 草稿纸管理

        子类可以调用此方法来使用增强功能，然后调用自身的process_request

        Args:
            request_data: 请求数据
            context: 上下文信息
            enable_rag: 是否启用RAG自动加载
            enable_smart_select: 是否启用智能上下文选择
            context_sources: 上下文来源列表

        Yields:
            Dict: 流式响应事件
        """
        user_id = context.get("user_id", "unknown") if context else "unknown"
        session_id = context.get("session_id", "unknown") if context else "unknown"
        project_id = request_data.get("project_id") if isinstance(request_data, dict) else None
        self._output_schema = None
        self._output_constraint_template = None
        if isinstance(request_data, dict):
            schema_id = request_data.get("output_schema_id")
            if schema_id:
                registry = get_output_schema_registry()
                self._output_schema = registry.get_schema(schema_id)
            if request_data.get("output_schema"):
                self._output_schema = request_data.get("output_schema")
            if request_data.get("output_constraint_template"):
                self._output_constraint_template = request_data.get("output_constraint_template")
        self.set_current_session(user_id, session_id)
        self._current_project_id = project_id

        try:
            # 如果启用智能选择，先选择相关上下文
            if enable_smart_select:
                input_text = request_data.get("input", request_data.get("query", ""))
                selected_context = await self.smart_select_context(
                    session_id, user_id,
                    current_task=input_text[:200],
                    sources=context_sources or ["all"]
                )

                # 将选中的上下文添加到内部笔记
                await self.add_note(
                    session_id, user_id, "selected_context",
                    selected_context.get("combined", ""),
                    metadata={"sources": context_sources}
                )

            # 如果启用RAG，自动加载RAG内容
            if enable_rag:
                input_text = request_data.get("input", request_data.get("query", ""))
                rag_results = await self.auto_load_rag(
                    session_id, user_id,
                    query=input_text[:200],
                    top_k=3
                )

                if rag_results:
                    # 添加到内部笔记
                    await self.add_note(
                        session_id, user_id, "rag_results",
                        f"RAG检索到{len(rag_results)}条相关内容",
                        metadata={"result_count": len(rag_results)}
                    )

            # 调用子类的process_request
            async for event in self.process_request(request_data, context):
                yield event

        except Exception as e:
            self.logger.error(f"增强上下文处理失败: {e}")
            yield await self._emit_event("error", f"处理失败: {str(e)}")
        finally:
            self.clear_current_session()
            self._output_schema = None
            self._output_constraint_template = None

    def _compact_text(self, text: str, max_chars: int) -> str:
        if not text:
            return ""
        if len(text) <= max_chars:
            return text
        return text[:max_chars].rstrip() + "…"

    def _is_memory_enabled(self, user_id: str, project_id: Optional[str]) -> bool:
        try:
            settings = get_memory_settings_manager().get_settings(user_id, project_id)
            return bool(settings.effective_enabled)
        except Exception:
            return True

    def _format_user_profile(self, profile: Any) -> str:
        if not profile:
            return ""
        parts = []
        if getattr(profile, "fav_genres", None):
            parts.append(f"偏好题材: {', '.join(profile.fav_genres)}")
        if getattr(profile, "avoid_tropes", None):
            parts.append(f"避雷桥段: {', '.join(profile.avoid_tropes)}")
        if getattr(profile, "language_style", None):
            parts.append(f"语言风格: {', '.join(profile.language_style)}")
        return " | ".join(parts)

    async def _build_context_pack(
        self,
        user_id: str,
        session_id: str,
        user_input: str
    ) -> List[Dict[str, Any]]:
        """
        构建结构化上下文打包信息（系统消息）

        优先走五层 Agent Memory（常驻短索引 + 历史按需召回）；
        再补充剧本/图/Notes 等会话工件摘要。
        """
        if not self.context_pack_enabled:
            return []
        if not self._is_memory_enabled(user_id, self._current_project_id):
            return []

        blocks: List[str] = []
        drama_id = getattr(self, "_current_project_id", None) or getattr(self, "_current_drama_id", None)

        # 五层记忆工作包（常驻优先，情节/语义 top-k，不全量注入）
        try:
            from utils.agent_memory import get_agent_memory_service

            bundle = get_agent_memory_service().assemble_working_memory(
                user_id=user_id,
                drama_id=drama_id,
                query=user_input or "",
                budget_chars=min(int(getattr(self, "context_pack_max_chars", 8000) or 8000), 8000),
            )
            prompt_block = bundle.to_prompt_block()
            if prompt_block.strip():
                blocks.append(prompt_block)
        except Exception:
            # 回退：旧用户画像 + 中期摘要
            try:
                profile_manager = get_user_profile_manager()
                profile = await profile_manager.get_profile(user_id)
                profile_text = self._format_user_profile(profile)
                if profile_text:
                    blocks.append(f"【用户画像】{profile_text}")
            except Exception:
                pass
            try:
                memory_manager = get_unified_memory_manager()
                mid = await memory_manager.get_middle_term_context(
                    user_id, session_id, user_input, limit=self.context_middle_term_limit
                )
                mid_text = mid.get("formatted_context", "")
                if mid_text and "暂无相关历史任务记录" not in mid_text:
                    blocks.append(f"【中期记忆】\n{mid_text}")
            except Exception:
                pass

        # 剧本结构摘要
        try:
            script_summary = await self.get_script_summary(user_id, session_id)
            if script_summary and "暂无" not in script_summary:
                blocks.append(f"【剧本结构摘要】\n{script_summary}")
        except Exception:
            pass

        # 图结构摘要
        try:
            graph_summary = await self.get_graph_summary(user_id, session_id)
            if graph_summary and "暂无" not in graph_summary:
                blocks.append(f"【图结构摘要】\n{graph_summary}")
        except Exception:
            pass

        # Notes（压缩）
        try:
            notes_context = await self.build_notes_context(user_id, session_id)
            if notes_context and "无Notes信息" not in notes_context:
                blocks.append(f"【Notes摘要】\n{notes_context}")
        except Exception:
            pass

        if not blocks:
            return []

        combined = "【ContextPack】\n" + "\n\n".join(blocks)
        combined = self._compact_text(combined, self.context_pack_max_chars)

        return [{"role": "system", "content": combined}]

    async def _build_context_tail(
        self,
        user_id: str,
        session_id: str,
        user_input: str
    ) -> Optional[Dict[str, Any]]:
        """
        构建上下文尾部提示，用于降低“中间遗忘”
        """
        if not self.context_pack_enabled:
            return None
        if not self._is_memory_enabled(user_id, self._current_project_id):
            return None

        parts: List[str] = []
        try:
            profile_manager = get_user_profile_manager()
            profile = await profile_manager.get_profile(user_id)
            profile_text = self._format_user_profile(profile)
            if profile_text:
                parts.append(f"用户偏好: {profile_text}")
        except Exception:
            pass

        try:
            script_summary = await self.get_script_summary(user_id, session_id)
            if script_summary and "暂无" not in script_summary:
                parts.append(self._compact_text(script_summary, 260))
        except Exception:
            pass

        if not parts:
            return None

        tail_text = "【ContextTail】\n【关键上下文（请优先遵守）】\n" + "\n".join(parts)
        tail_text = self._compact_text(tail_text, self.context_tail_max_chars)
        return {"role": "system", "content": tail_text}

    async def build_messages_with_context(
        self,
        user_input: str,
        user_id: str = "unknown",
        session_id: str = "unknown",
        enable_rag: bool = False,
        include_scratchpad: bool = False,
        scratchpad_task: str = "",
        input_data: Dict[str, Any] = None,
        enable_style_examples: bool = True,
        style_example_count: int = 2,
        enable_story_facts: bool = True,
        max_facts: int = 20,
        enable_personalized_style: bool = True
    ) -> List[Dict[str, str]]:
        """
        构建带增强上下文的消息列表

        🆕 支持风格示例注入、故事事实注入、个性化风格注入

        Args:
            user_input: 用户输入
            user_id: 用户ID
            session_id: 会话ID
            enable_rag: 是否启用RAG自动加载
            include_scratchpad: 是否包含草稿纸内容
            scratchpad_task: 草稿纸选择任务描述
            input_data: 完整的输入数据（用于风格检测）
            enable_style_examples: 是否启用风格示例注入
            style_example_count: 每个风格的示例数量
            enable_story_facts: 是否启用故事事实注入
            max_facts: 最大事实数量
            enable_personalized_style: 是否启用个性化风格注入（从用户历史编辑学习）

        Returns:
            构建好的消息列表

        Prompt-cache（OpenClaw/Pi）：
        - self.system_prompt 保持 stable prefix
        - 故事事实 / ContextPack / 风格示例等易变内容进 dynamic suffix（_cacheable=False）
        """
        # 稳定前缀：仅基础 system prompt（跨 turn 字节级稳定）
        system_content = self.system_prompt

        extra_messages: List[Dict[str, Any]] = []
        dynamic_blocks: List[str] = []

        # 易变：故事事实 → dynamic（勿拼进 stable system）
        if enable_story_facts and session_id != "unknown":
            facts_constraints = await self._inject_story_facts(session_id, max_facts)
            if facts_constraints:
                dynamic_blocks.append(facts_constraints)
                self.logger.debug(f"✅ 注入故事事实约束 (session_id: {session_id})")

        # 易变：个性化风格示例
        if enable_personalized_style and user_id != "unknown":
            personalized_messages = await self._inject_personalized_style_examples(
                user_input=user_input,
                user_id=user_id,
                count=3
            )
            if personalized_messages:
                dynamic_blocks.append(
                    "【您的写作风格】以下是您过去修改时的写作风格示例，请尽量模仿这种风格：\n\n"
                    + "\n\n".join([msg["content"] for msg in personalized_messages])
                )
                self.logger.debug(f"✅ 注入 {len(personalized_messages)} 条个性化风格示例")

        # 易变：通用风格示例
        if enable_style_examples:
            style_messages = await self._inject_style_examples(
                input_data or {"input": user_input},
                style_example_count
            )
            if style_messages:
                dynamic_blocks.append(
                    "【参考风格示例】请参考以下对话风格：\n\n"
                    + "\n\n".join(
                        [
                            f"用户: {msg['content']}" if msg["role"] == "user" else f"助手: {msg['content']}"
                            for msg in style_messages
                        ]
                    )
                )
                self.logger.debug(f"✅ 注入 {len(style_messages)} 条通用风格示例")

        # 易变：结构化上下文包
        context_pack = await self._build_context_pack(user_id, session_id, user_input)
        if context_pack:
            for pack_msg in context_pack:
                content = pack_msg.get("content") or ""
                if content:
                    dynamic_blocks.append(str(content))

        if dynamic_blocks:
            extra_messages.append(
                {
                    "role": "system",
                    "content": "\n\n".join(dynamic_blocks),
                    "_cacheable": False,
                }
            )

        # 如果启用RAG，使用rebuild_context_with_rag
        if enable_rag:
            messages = await self.rebuild_context_with_rag(
                session_id, user_id,
                system_content,
                user_input,
                enable_auto_rag=True,
                max_rag_items=3,
                extra_messages=extra_messages
            )
        else:
            # 否则使用普通的rebuild_optimized_context
            messages = await self.rebuild_optimized_context(
                session_id, user_id, user_input, extra_messages=extra_messages
            )

        # 如果需要包含草稿纸内容
        if include_scratchpad and scratchpad_task:
            scratchpad_items = await self.select_from_scratchpad(
                session_id, user_id,
                current_task=scratchpad_task,
                max_items=3
            )

            if scratchpad_items:
                scratchpad_content = "\n\n".join([
                    f"- {item.get('content', '')[:300]}"
                    for item in scratchpad_items
                ])
                # 找到合适的插入位置（在风格示例之后）
                insert_pos = 1
                if enable_style_examples or enable_personalized_style:
                    # 跳过风格示例消息
                    for i in range(1, min(len(messages), 10)):
                        if messages[i].get('role') not in ['user', 'assistant']:
                            insert_pos = i + 1
                        else:
                            insert_pos = i + 1
                            if messages[i].get('role') == 'assistant':
                                break

                messages.insert(insert_pos, {
                    "role": "system",
                    "content": f"【相关信息】\n{scratchpad_content}"
                })

        # 🆕 追加上下文尾部提示（降低“中间遗忘”）
        tail_context = await self._build_context_tail(user_id, session_id, user_input)
        if tail_context and messages:
            insert_pos = max(0, len(messages) - 1)
            messages.insert(insert_pos, tail_context)

        return messages

    async def _inject_style_examples(
        self,
        input_data: Dict[str, Any],
        count: int = 2
    ) -> List[Dict[str, str]]:
        """
        注入风格示例

        Args:
            input_data: 输入数据
            count: 每个风格的示例数量

        Returns:
            List[Dict]: 示例消息列表
        """
        try:
            from utils.style_library_manager import get_style_library_manager
            manager = await get_style_library_manager()
            return await manager.get_fewshot_messages(input_data, count)
        except Exception as e:
            self.logger.warning(f"风格示例注入失败: {e}")
            return []

    async def _inject_personalized_style_examples(
        self,
        user_input: str,
        user_id: str = "unknown",
        count: int = 3
    ) -> List[Dict[str, str]]:
        """
        🆕 注入个性化风格示例（从用户历史编辑中学习）

        从 Milvus 向量库中检索与当前输入最相似的用户编辑片段，
        作为 Few-Shot Examples 注入到 Prompt 中。

        Args:
            user_input: 用户输入文本
            user_id: 用户ID
            count: 返回示例数量

        Returns:
            List[Dict]: 风格示例消息列表
        """
        try:
            from utils.memory_manager import get_style_memory

            # 获取风格向量库
            style_memory = get_style_memory()

            # 搜索相似的风格片段
            fragments = await style_memory.search_similar(
                query_text=user_input,
                user_id=user_id,
                top_k=count
            )

            if not fragments:
                self.logger.debug(f"未找到用户 {user_id} 的历史风格片段")
                return []

            # 转换为消息格式
            messages = []
            for frag in fragments:
                # 构建示例消息
                messages.append({
                    "role": "user",
                    "content": f"【参考风格示例】以下是您之前的修改风格：\n{frag.modified_text}"
                })

            self.logger.info(f"✅ 注入 {len(fragments)} 条个性化风格示例 (user: {user_id})")
            return messages

        except Exception as e:
            self.logger.warning(f"个性化风格示例注入失败: {e}")
            return []

    async def _inject_story_facts(
        self,
        session_id: str,
        max_facts: int = 20
    ) -> str:
        """
        注入故事事实约束

        从 Redis 获取会话的故事事实并生成约束文本。

        Args:
            session_id: 会话 ID
            max_facts: 最大事实数量

        Returns:
            str: 事实约束文本，如果没有事实则返回空字符串
        """
        try:
            from utils.story_fact_manager import generate_constraints_prompt
            return await generate_constraints_prompt(session_id, max_facts)
        except Exception as e:
            self.logger.warning(f"故事事实注入失败: {e}")
            return ""

    # 子类可覆盖：允许 spawn 的专家白名单；None 表示不限制
    allowed_subagents: Optional[List[str]] = None

    async def spawn_subagent(
        self,
        agent_id: str,
        task: str,
        *,
        context: Optional[Dict[str, Any]] = None,
        context_keys: Optional[List[str]] = None,
        timeout: float = 120,
        depth: int = 0,
    ) -> Dict[str, Any]:
        """统一 Agent-as-tool：调用子专家并返回聚合结果。"""
        from utils.agent_infra.subagents import SubagentRunner, SubagentSpec

        allow = set(self.allowed_subagents) if self.allowed_subagents is not None else None
        runner = SubagentRunner()
        result = await runner.spawn(
            SubagentSpec(
                agent_id=agent_id,
                task=task,
                context_keys=list(context_keys or []),
                timeout=timeout,
            ),
            parent_agent_id=getattr(self, "agent_name", "") or "",
            context=context,
            depth=depth,
            allowed_subagents=allow,
        )
        return {
            "success": result.success,
            "tool_name": result.agent_id,
            "tool_agent": result.agent_id,
            "result": result.content,
            "error": result.error,
            "checkpoint_id": result.checkpoint_id,
            "duration_ms": result.duration_ms,
        }

    async def handoff_to(
        self,
        agent_id: str,
        *,
        session_id: str,
        reason: str = "",
        context_keys: Optional[List[str]] = None,
        payload_ref: str = "",
    ) -> Dict[str, Any]:
        """会话级交接：下一轮由目标专家直接对用户说话。"""
        from utils.agent_infra.handoffs import apply_handoff
        from utils.agent_infra.orchestration import HandoffSpec

        spec = HandoffSpec(
            from_agent=getattr(self, "agent_name", "") or "",
            to_agent=agent_id,
            reason=reason or "handoff",
            context_keys=list(context_keys or []),
            payload_ref=payload_ref,
        )
        state = apply_handoff(session_id or "default", spec)
        return {"success": True, "handoff": spec.to_dict(), "session": state.to_dict()}

    def get_agent_info(self) -> Dict[str, Any]:
        """获取Agent信息"""
        return {
            "name": self.agent_name,
            "agent_name": self.agent_name,
            "model_provider": self.model_provider,
            "system_prompt_length": len(self.system_prompt),
            "config": {
                "log_level": self.config.log_level,
                "default_provider": self.config.default_provider
            }
        }
    
    def get_performance_info(self) -> Dict[str, Any]:
        """获取性能信息"""
        try:
            # 获取Agent性能统计
            agent_performance = self.performance_monitor.get_agent_performance(self.agent_name)

            # 获取健康状态
            health_status = self.performance_monitor.get_agent_health(self.agent_name)

            return {
                "agent_name": self.agent_name,
                "performance_stats": agent_performance,
                "health_status": health_status.to_dict() if health_status else None,
                "monitoring_enabled": True
            }
        except Exception as e:
            self.logger.error(f"获取性能信息失败: {e}")
            return {
                "agent_name": self.agent_name,
                "performance_stats": {},
                "health_status": None,
                "monitoring_enabled": False,
                "error": str(e)
            }

    # ==================== 反馈追踪方法 ====================

    def generate_trace_id(self) -> str:
        """
        🆕 生成追踪ID

        在每次生成内容前调用，用于关联用户反馈

        Returns:
            str: 唯一的追踪ID
        """
        import time
        import uuid
        timestamp = int(time.time() * 1000)
        unique = uuid.uuid4().hex[:8]
        trace_id = f"trace_{timestamp}_{unique}"
        self._current_trace_id = trace_id
        return trace_id

    def get_current_trace_id(self) -> Optional[str]:
        """
        🆕 获取当前追踪ID

        Returns:
            Optional[str]: 当前追踪ID，如果没有则返回None
        """
        return self._current_trace_id

    def set_trace_id(self, trace_id: str) -> None:
        """
        🆕 设置追踪ID

        Args:
            trace_id: 追踪ID
        """
        self._current_trace_id = trace_id

    def clear_trace_id(self) -> None:
        """🆕 清除追踪ID"""
        self._current_trace_id = None

    async def record_success_feedback(
        self,
        user_input: str,
        ai_output: str,
        user_id: str = "unknown",
        session_id: str = "unknown"
    ) -> bool:
        """
        🆕 记录成功反馈

        当Agent认为某次生成特别成功时，可以调用此方法记录。

        Args:
            user_input: 用户输入
            ai_output: AI输出
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            bool: 是否记录成功
        """
        try:
            trace_id = self._current_trace_id or self.generate_trace_id()

            from utils.feedback_manager import record_agent_success
            return await record_agent_success(
                trace_id=trace_id,
                agent_name=self.agent_name,
                user_input=user_input,
                ai_output=ai_output,
                user_id=user_id,
                session_id=session_id
            )
        except Exception as e:
            self.logger.warning(f"记录成功反馈失败: {e}")
            return False

    # ==================== 统一输出格式化方法 ====================

    def format_output(
        self,
        success: bool,
        data: Any = None,
        message: str = "",
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        code: int = 200
    ) -> Dict[str, Any]:
        """
        🎯 统一输出格式化方法 - 所有Agent必须使用此方法格式化输出

        确保所有40+个Agent输出一致的结构，便于后期合并和处理

        Args:
            success: 是否成功
            data: 主要数据内容
            message: 提示消息
            error: 错误信息（如果失败）
            metadata: 额外元数据
            code: 状态码 (默认200)

        Returns:
            统一格式的字典

        输出格式规范：
        {
            "code": 200,                    # 状态码: 200成功, 400客户端错误, 500服务端错误
            "success": true,                # 是否成功
            "message": "操作成功",           # 提示消息
            "data": {...},                  # 主要数据内容
            "error": null,                  # 错误信息（仅失败时）
            "metadata": {                   # 元数据
                "agent_name": "xxx",
                "timestamp": "2025-xx-xx",
                "processing_time": 1.23,
                ...
            },
            "trace_id": "uuid"              # 追踪ID
        }
        """
        from datetime import datetime
        import uuid

        # 构建基础元数据
        base_metadata = {
            "agent_name": self.agent_name,
            "model_provider": self.model_provider,
            "timestamp": datetime.now().isoformat(),
            "trace_id": str(uuid.uuid4())
        }

        # 合并用户提供的元数据
        if metadata:
            base_metadata.update(metadata)

        # 构建输出
        output = {
            "code": code,
            "success": success,
            "message": message,
            "data": data,
            "error": error,
            "metadata": base_metadata
        }

        return output

    def to_json(self, output_dict: Dict[str, Any], ensure_ascii: bool = False) -> str:
        """
        将输出转换为JSON字符串

        Args:
            output_dict: format_output()返回的字典
            ensure_ascii: 是否确保ASCII编码（中文转Unicode）

        Returns:
            JSON字符串
        """
        try:
            import json
            return json.dumps(output_dict, ensure_ascii=ensure_ascii, indent=2)
        except Exception as e:
            self.logger.error(f"转换为JSON失败: {e}")
            # 返回简单的错误JSON
            return json.dumps({
                "code": 500,
                "success": False,
                "message": "JSON序列化失败",
                "error": str(e),
                "data": None
            }, ensure_ascii=ensure_ascii)

    def format_success(
        self,
        data: Any = None,
        message: str = "操作成功",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        快捷方法：格式化成功输出

        Args:
            data: 主要数据
            message: 成功消息
            metadata: 元数据

        Returns:
            成功格式的字典

        Example:
            return self.format_success(
                data={"plot": "剧情内容..."},
                message="剧本生成成功",
                metadata={"plot_type": "复仇"}
            )
        """
        return self.format_output(
            success=True,
            data=data,
            message=message,
            metadata=metadata,
            code=200
        )

    def format_error(
        self,
        error: str,
        message: str = "操作失败",
        code: int = 500,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        快捷方法：格式化错误输出

        Args:
            error: 错误信息
            message: 错误提示
            code: 错误码 (默认500)
            metadata: 元数据

        Returns:
            错误格式的字典

        Example:
            return self.format_error(
                error="LLM调用超时",
                message="剧本生成失败，请重试",
                code=504,
                metadata={"timeout": 30}
            )
        """
        return self.format_output(
            success=False,
            data=None,
            message=message,
            error=error,
            metadata=metadata,
            code=code
        )

    def format_stream_event(
        self,
        event_type: str,
        data: Any = None,
        message: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        格式化流式事件输出

        Args:
            event_type: 事件类型 (如: "thinking", "progress", "result", "error")
            data: 事件数据
            message: 事件消息
            metadata: 元数据

        Returns:
            流式事件格式字典

        Example:
            yield self.format_stream_event(
                event_type="progress",
                data={"percent": 50},
                message="正在生成剧本..."
            )
        """
        from datetime import datetime

        event = {
            "type": event_type,
            "data": data,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "agent_name": self.agent_name
        }

        if metadata:
            event["metadata"] = metadata

        return event

    async def validate_output_format(
        self,
        output: Dict[str, Any],
        required_fields: Optional[List[str]] = None
    ) -> bool:
        """
        验证输出格式是否符合规范

        Args:
            output: 待验证的输出字典
            required_fields: 必需字段列表

        Returns:
            是否符合规范
        """
        # 基础必需字段
        base_required = ["code", "success", "message"]
        if required_fields:
            base_required.extend(required_fields)

        # 检查必需字段
        for field in base_required:
            if field not in output:
                self.logger.error(f"输出格式验证失败: 缺少字段 '{field}'")
                return False

        # 验证code范围
        code = output.get("code", 0)
        if not isinstance(code, int) or code < 100 or code >= 600:
            self.logger.error(f"输出格式验证失败: 无效的code '{code}'")
            return False

        # 验证success类型
        success = output.get("success")
        if not isinstance(success, bool):
            self.logger.error(f"输出格式验证失败: success必须是布尔值")
            return False

        # 成功时应该有data，失败时应该有error
        if success and "data" not in output:
            self.logger.warning("输出格式警告: 成功响应缺少data字段")
        if not success and "error" not in output:
            self.logger.warning("输出格式警告: 失败响应缺少error字段")

        return True

    def format_batch_results(
        self,
        results: List[Dict[str, Any]],
        total: int,
        successful: int,
        failed: int,
        message: str = ""
    ) -> Dict[str, Any]:
        """
        格式化批量处理结果

        Args:
            results: 结果列表
            total: 总数
            successful: 成功数
            failed: 失败数
            message: 提示消息

        Returns:
            批量结果格式字典

        Example:
            return self.format_batch_results(
                results=[result1, result2, ...],
                total=10,
                successful=8,
                failed=2,
                message="批量处理完成"
            )
        """
        return self.format_success(
            data={
                "results": results,
                "summary": {
                    "total": total,
                    "successful": successful,
                    "failed": failed,
                    "success_rate": f"{(successful/total*100):.1f}%" if total > 0 else "0%"
                }
            },
            message=message or f"批量处理完成: {successful}/{total} 成功",
            metadata={
                "batch_mode": True,
                "total_count": total,
                "failed_count": failed
            }
        )
    
    def _with_performance_monitoring(self, operation: str):
        """性能监控装饰器"""
        def decorator(func):
            async def async_wrapper(*args, **kwargs):
                with PerformanceContext(
                    self.performance_monitor,
                    self.agent_name,
                    operation,
                    {"function": func.__name__, "args_count": len(args)}
                ) as context:
                    try:
                        result = await func(*args, **kwargs)
                        return result
                    except Exception as e:
                        context.success = False
                        context.error_message = str(e)
                        raise
            
            def sync_wrapper(*args, **kwargs):
                with PerformanceContext(
                    self.performance_monitor,
                    self.agent_name,
                    operation,
                    {"function": func.__name__, "args_count": len(args)}
                ) as context:
                    try:
                        result = func(*args, **kwargs)
                        return result
                    except Exception as e:
                        context.success = False
                        context.error_message = str(e)
                        raise
            
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        return decorator
    
    # ==================== 多轮对话上下文管理方法（增强版） ====================
    
    async def create_conversation_context(
        self, 
        user_id: str, 
        session_id: str, 
        initial_query: str
    ):
        """创建对话上下文（ ）"""
        return await self.storage_manager.create_conversation_context(
            user_id=user_id,
            session_id=session_id,
            initial_query=initial_query
        )
    
    async def get_conversation_context(self, user_id: str, session_id: str):
        """获取对话上下文"""
        return await self.storage_manager.get_conversation_context(user_id, session_id)
    
    async def update_conversation_context(
        self, 
        user_id: str, 
        session_id: str, 
        updates: Dict[str, Any]
    ):
        """更新对话上下文"""
        return await self.storage_manager.update_conversation_context(
            user_id, session_id, updates
        )
    
    async def add_user_message(
        self, 
        user_id: str, 
        session_id: str, 
        message: str, 
        mark_as_new: bool = True
    ):
        """添加用户消息到对话上下文"""
        return await self.storage_manager.add_user_message(
            user_id, session_id, message, mark_as_new
        )
    
    async def add_orchestrator_call(
        self, 
        user_id: str, 
        session_id: str, 
        instruction: str
    ):
        """添加orchestrator调用记录"""
        return await self.storage_manager.add_orchestrator_call(
            user_id, session_id, instruction
        )
    
    async def add_conversation_message(
        self, 
        user_id: str, 
        session_id: str, 
        role: str, 
        content: str,
        agent_source: Optional[str] = None
    ):
        """添加对话消息"""
        return await self.storage_manager.add_conversation_message(
            user_id, session_id, role, content, agent_source or self.agent_name
        )
    
    async def format_context_for_prompt(
        self,
        user_id: str,
        session_id: str,
        include_user_queue: bool = True,
        include_notes: bool = True,
        include_files: bool = True,
        selected_notes: Optional[List[str]] = None,
        include_chat_history: bool = False,
        include_orchestrator_timeline: bool = False
    ) -> str:
        """格式化上下文用于提示词（ ）"""
        try:
            context = await self.get_conversation_context(user_id, session_id)
            if not context:
                return "无上下文信息"
            
            context_parts = []
            
            # 1. 用户消息队列
            if include_user_queue and context.user_message_queue:
                context_parts.append("## 用户消息队列")
                for i, msg in enumerate(context.user_message_queue[-5:], 1):  # 最近5条
                    is_new = "🆕" if msg.get('is_new', False) else ""
                    context_parts.append(f"{i}. {is_new}{msg.get('content', '')}")
            
            # 2. 创建的Notes
            if include_notes and context.created_notes:
                context_parts.append("## 已创建的Notes")
                for note in context.created_notes:
                    select_status = "✅" if note.get('select', 0) > 0 else "⭕"
                    context_parts.append(f"- {select_status} {note.get('name', '')}: {note.get('title', '')}")
                    if note.get('context'):
                        context_parts.append(f"  {note.get('context', '')}")
            
            # 3. 对话历史
            if include_chat_history and context.conversation_history:
                context_parts.append("## 对话历史")
                for msg in context.conversation_history[-10:]:  # 最近10条
                    role = msg.get('role', 'user')
                    content = msg.get('content', '')
                    timestamp = msg.get('timestamp', '')
                    context_parts.append(f"[{role}] {content}")
            
            # 4. Orchestrator时间线
            if include_orchestrator_timeline and context.orchestrator_calls:
                context_parts.append("## Orchestrator调用时间线")
                for call in context.orchestrator_calls[-5:]:  # 最近5次调用
                    instruction = call.get('instruction', '')
                    timestamp = call.get('timestamp', '')
                    context_parts.append(f"- {timestamp}: {instruction}")
            
            # 5. 上下文摘要（如果已压缩）
            if context.is_compressed and context.context_summary:
                context_parts.append("## 上下文摘要")
                context_parts.append(context.context_summary)
            
            return "\n".join(context_parts) if context_parts else "无上下文信息"
            
        except Exception as e:
            self.logger.error(f"格式化上下文失败: {e}")
            return "上下文格式化失败"
    
    # 保持向后兼容的旧方法
    async def create_context(
        self, 
        user_id: str, 
        session_id: str, 
        initial_query: str
    ):
        """创建上下文（向后兼容）"""
        return await self.create_conversation_context(user_id, session_id, initial_query)
    
    async def get_context(self, user_id: str, session_id: str):
        """获取上下文（向后兼容）"""
        return await self.get_conversation_context(user_id, session_id)
    
    async def update_context(self, user_id: str, session_id: str, updates: Dict[str, Any]):
        """更新上下文（向后兼容）"""
        return await self.update_conversation_context(user_id, session_id, updates)
    
    # ==================== 停止管理方法（新增） ====================
    
    def set_current_session(self, user_id: str, session_id: str):
        """设置当前执行的会话信息"""
        self.current_user_id = user_id
        self.current_session_id = session_id
        # 🎯 同时记录用于流式事件存储
        self._current_user_id = user_id
        self._current_session_id = session_id
    
    def clear_current_session(self):
        """清除当前执行的会话信息"""
        self.current_user_id = None
        self.current_session_id = None
        self._current_user_id = None
        self._current_session_id = None
        self._current_project_id = None
    
    async def check_stop_status(self, user_id: str, session_id: str, current_step: Optional[str] = None) -> bool:
        """检查是否已请求停止"""
        try:
            if self.stop_manager:
                return await self.stop_manager.is_stopped(user_id, session_id)
            else:
                # 尝试直接导入停止管理器
                from utils.stop_manager import get_juben_stop_manager
                stop_manager = await get_juben_stop_manager()
                return await stop_manager.is_stopped(user_id, session_id)
        except ImportError:
            # 如果停止管理器不存在，返回False
            return False
        except Exception as e:
            self.logger.warning(f"⚠️ 检查停止状态失败: {e}")
            return False
    
    async def check_and_raise_if_stopped(self, user_id: str, session_id: str, current_step: Optional[str] = None):
        """检查停止状态，如果已停止则抛出异常"""
        try:
            if self.stop_manager:
                await self.stop_manager.check_and_raise_if_stopped(user_id, session_id, current_step)
            else:
                # 尝试直接导入停止管理器
                from utils.stop_manager import get_juben_stop_manager, JubenStoppedException
                stop_manager = await get_juben_stop_manager()
                await stop_manager.check_and_raise_if_stopped(user_id, session_id, current_step)
        except ImportError:
            # 如果停止管理器不存在，跳过检查
            pass
        except Exception as e:
            self.logger.warning(f"⚠️ 检查停止状态异常: {e}")
    
    async def request_stop(self, user_id: str, session_id: str, reason: str = "user_request", message: Optional[str] = None):
        """请求停止当前执行"""
        try:
            from utils.stop_manager import StopReason
            
            if self.stop_manager:
                stop_reason = StopReason.USER_REQUEST if reason == "user_request" else StopReason.ERROR
                return await self.stop_manager.request_stop(
                    user_id=user_id,
                    session_id=session_id,
                    reason=stop_reason,
                    message=message,
                    agent_name=self.agent_name
                )
            else:
                # 尝试直接导入停止管理器
                from utils.stop_manager import get_juben_stop_manager
                stop_manager = await get_juben_stop_manager()
                stop_reason = StopReason.USER_REQUEST if reason == "user_request" else StopReason.ERROR
                return await stop_manager.request_stop(
                    user_id=user_id,
                    session_id=session_id,
                    reason=stop_reason,
                    message=message,
                    agent_name=self.agent_name
                )
        except ImportError:
            self.logger.warning(f"⚠️ 停止管理器不可用，无法请求停止")
            return False
        except Exception as e:
            self.logger.error(f"❌ 请求停止失败: {e}")
            return False
    
    async def clear_stop_state(self, user_id: str, session_id: str) -> bool:
        """清除停止状态"""
        try:
            if self.stop_manager:
                return await self.stop_manager.clear_stop_state(user_id, session_id)
            else:
                # 尝试直接导入停止管理器
                from utils.stop_manager import get_juben_stop_manager
                stop_manager = await get_juben_stop_manager()
                return await stop_manager.clear_stop_state(user_id, session_id)
        except ImportError:
            return True
        except Exception as e:
            self.logger.error(f"❌ 清除停止状态失败: {e}")
            return False
    
    # ==================== 多模态处理方法（新增） ====================
    
    async def get_file_content_for_processing(self, user_id: str, session_id: str, file_refs: List[str]) -> Dict[str, Any]:
        """获取文件内容用于Agent处理"""
        try:
            # 尝试使用多模态处理器
            from utils.multimodal_processor import get_multimodal_processor
            processor = get_multimodal_processor()
            return await processor.get_file_content_for_agent(user_id, session_id, file_refs)
        except ImportError:
            self.logger.warning(f"⚠️ 多模态处理器不可用，跳过文件处理")
            return {"files": [], "content": ""}
    
    async def extract_file_references_from_text(self, text: str) -> List[str]:
        """从文本中提取文件引用"""
        import re
        file_refs = []
        
        # 提取@文件引用
        pattern = r'@(file\d+|image\d+|document\d+|pdf\d+|excel\d+|audio\d+)'
        matches = re.findall(pattern, text)
        file_refs.extend(matches)
        
        return file_refs
    
    # ==================== Notes系统方法（新增） ====================
    
    async def create_note(
        self,
        user_id: str,
        session_id: str,
        action: str,  # drama_planning/drama_creation/drama_evaluation等
        name: str,    # note1, note2, etc.
        context: str, # 内容
        title: Optional[str] = None,  # 标题
        select: int = None,  # 选择状态
        note_id: Optional[str] = None
    ) -> bool:
        """创建note (统一接口) - 🎯 支持自动设置选择状态"""
        
        # 🎯 根据action类型自动设置选择状态
        if select is None:
            select = self._get_auto_select_status(action)
        
        try:
            # 使用存储管理器保存note
            note = Note(
                user_id=user_id,
                session_id=session_id,
                action=action,
                name=name,
                title=title,
                context=context,
                select_status=select,
                metadata={"agent_source": self.agent_name}
            )
            
            note_id = await self.storage_manager.save_note(note)
            if note_id:
                select_status = "自动选中" if select == 1 else "等待选择"
                self.logger.info(f"📝 创建note成功: user_id={user_id}, session_id={session_id}, action={action}, name={name}, 状态={select_status}")
                return True
            else:
                self.logger.warning(f"⚠️ 创建note失败: user_id={user_id}, session_id={session_id}, action={action}, name={name}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 创建note异常: user_id={user_id}, session_id={session_id}, action={action}, name={name}, error={e}")
            return False
    
    def _get_auto_select_status(self, action: str) -> int:
        """🎯 根据action类型自动确定选择状态"""
        # 自动选中的action类型（不需要用户选择）
        AUTO_SELECT_ACTIONS = {
            'websearch', 'knowledge', 'analysis', 'evaluation'
        }
        
        # 需要用户选择的action类型
        USER_SELECT_ACTIONS = {
            'drama_planning', 'drama_creation', 'drama_evaluation', 
            'character_development', 'plot_development', 'story_analysis'
        }
        
        if action in AUTO_SELECT_ACTIONS:
            return 1  # 自动选中
        elif action in USER_SELECT_ACTIONS:
            return 0  # 等待用户选择
        else:
            # 未知action类型，默认需要用户选择
            self.logger.warning(f"⚠️ 未知action类型: {action}，默认设置为需要用户选择")
            return 0
    
    async def get_note_by_name(self, user_id: str, session_id: str, name: str) -> Optional[Dict[str, Any]]:
        """根据name获取note"""
        try:
            notes = await self.storage_manager.get_notes(user_id, session_id, None)
            for note in notes:
                if note.get('name') == name:
                    return note
            return None
        except Exception as e:
            self.logger.error(f"❌ 获取note失败: {e}")
            return None
    
    async def get_notes_by_action(self, user_id: str, session_id: str, action: str) -> List[Dict[str, Any]]:
        """根据action获取notes"""
        try:
            notes = await self.storage_manager.get_notes(user_id, session_id, action)
            return notes
        except Exception as e:
            self.logger.error(f"❌ 获取notes失败: {e}")
            return []
    
    async def update_note_select(self, user_id: str, session_id: str, note_name: str, select_status: int) -> bool:
        """更新note选择状态"""
        try:
            # 这里需要实现更新note选择状态的逻辑
            # 暂时返回True
            self.logger.info(f"📝 更新note选择状态: {note_name} -> {select_status}")
            return True
        except Exception as e:
            self.logger.error(f"❌ 更新note选择状态失败: {e}")
            return False
    
    async def get_selected_notes_names(self, user_id: str, session_id: str, action: Optional[str] = None) -> List[str]:
        """获取选中的notes名称列表"""
        try:
            notes = await self.get_notes_by_action(user_id, session_id, action or "")
            selected_names = []
            for note in notes:
                if note.get('select_status', 0) == 1:  # 选中状态
                    selected_names.append(note.get('name', ''))
            return selected_names
        except Exception as e:
            self.logger.error(f"❌ 获取选中notes失败: {e}")
            return []
    
    async def get_next_action_id(self, user_id: str, session_id: str, action: str) -> int:
        """
        获取会话内某个action类型的下一个可用ID（按action类型递增）
        🚀 【性能优化】使用Redis的INCR原子操作确保唯一性和递增性
        """
        try:
            # 构建Redis key，按action类型区分
            redis_key = f"action_id:{user_id}:{session_id}:{action}"
            
            # 🚀 【关键】获取Redis客户端并使用INCR操作获取下一个ID（原子操作，并发安全）
            redis_client = await self._get_redis_client()
            if redis_client:
                next_id = await redis_client.incr(redis_key)
                # 设置过期时间（24小时），避免Redis内存无限累积
                await redis_client.expire(redis_key, 86400)  # 24小时后自动清理
                self.logger.debug(f"🚀 Redis生成action ID: user_id={user_id}, session_id={session_id}, action={action}, id={next_id}")
                return next_id
            else:
                # Redis不可用，使用数据库查询方式
                existing_notes = await self.get_notes_by_action(user_id, session_id, action)
                fallback_id = len(existing_notes) + 1
                self.logger.warning(f"⚠️ Redis不可用，使用数据库查询方式生成action ID: {fallback_id}")
                return fallback_id
            
        except Exception as e:
            self.logger.error(f"❌ Redis生成action ID失败: {e}")
            # 最后的备用方案：使用时间戳+随机数
            timestamp_suffix = int(str(int(time.time() * 1000))[-6:])
            random_suffix = random.randint(100, 999)
            emergency_id = int(f"{timestamp_suffix}{random_suffix}")
            self.logger.warning(f"⚠️ 使用紧急备用方式生成action ID: {emergency_id}")
            return emergency_id
    
    async def build_notes_context(self, user_id: str, session_id: str) -> str:
        """构建notes上下文字符串"""
        try:
            notes = await self.storage_manager.get_notes(user_id, session_id, None)
            if not notes:
                return "无Notes信息"
            
            context_parts = []
            for note in notes:
                select_status = "✅" if note.get('select_status', 0) == 1 else "⭕"
                name = note.get('name', '')
                title = note.get('title', '')
                context = note.get('context', '')
                action = note.get('action', '')
                
                context_parts.append(f"- {select_status} [{action}] {name}: {title}")
                if context:
                    context_parts.append(f"  {context}")
            
            return "\n".join(context_parts) if context_parts else "无Notes信息"
        except Exception as e:
            self.logger.error(f"❌ 构建notes上下文失败: {e}")
            return "Notes上下文构建失败"
    
    # ==================== 智能引用解析方法（新增） ====================
    
    def extract_note_references(self, text: str) -> List[str]:
        """提取文本中的@引用"""
        import re
        # 提取@note引用
        pattern = r'@(note\d+|drama\d+|character\d+|plot\d+)'
        matches = re.findall(pattern, text)
        return matches
    
    def should_resolve(self, text: str) -> bool:
        """判断是否需要进行智能引用解析"""
        return '@' in text and any(keyword in text.lower() for keyword in ['note', 'drama', 'character', 'plot'])
    
    async def resolve_note_references(self, text: str, user_id: str, session_id: str) -> str:
        """解析文本中的引用（支持自然语言和@引用）"""
        try:
            # 提取引用
            references = self.extract_note_references(text)
            if not references:
                return text
            
            # 获取相关notes
            notes = await self.storage_manager.get_notes(user_id, session_id, None)
            note_dict = {note.get('name', ''): note for note in notes}
            
            # 替换引用
            resolved_text = text
            for ref in references:
                if ref in note_dict:
                    note = note_dict[ref]
                    context = note.get('context', '')
                    title = note.get('title', '')
                    resolved_text = resolved_text.replace(f'@{ref}', f'[{title}]{context}')
            
            return resolved_text
        except Exception as e:
            self.logger.error(f"❌ 解析引用失败: {e}")
            return text
    
    # ==================== 流式事件存储方法（新增） ====================
    
    async def emit_juben_event(
        self,
        event_type: str,
        data: Union[str, Dict[str, Any]] = "",
        metadata: Optional[Dict[str, Any]] = None,
        event_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """发送Juben专用事件（增强版：自动存储）"""
        # 生成事件ID
        if event_id is None:
            event_id = int(time.time() * 1000) + random.randint(1000, 9999)
        
        # 创建事件
        event = {
            "event_type": event_type,
            "agent_source": self.agent_name,
            "timestamp": datetime.now().isoformat(),
            "data": data,
            "metadata": metadata or {},
            "event_id": event_id
        }
        
        # 🎯 异步存储流式事件
        if self._stream_storage_enabled and self._current_user_id and self._current_session_id:
            asyncio.create_task(self._store_stream_event_async(event))
        
        return event
    
    async def _store_stream_event_async(self, event: Dict[str, Any]):
        """
        异步存储流式事件到数据库

        🆕 增强：现在会实际保存事件到数据库，并对最终结果进行自动保存
        """
        try:
            # 检查是否有存储管理器
            if not self.storage_manager:
                self.logger.debug(f"💾 跳过存储（无存储管理器）: {event['event_type']}")
                return

            # 获取当前用户和会话ID
            user_id = self._current_user_id or "unknown"
            session_id = self._current_session_id or "unknown"

            # 保存流式事件到数据库
            event_id = await self.storage_manager.save_stream_event(
                user_id=user_id,
                session_id=session_id,
                event_type=event.get("event_type", "unknown"),
                content_type="event",
                agent_source=event.get("agent_source", self.agent_name),
                event_data=event.get("data", ""),
                event_metadata=event.get("metadata", {})
            )

            if event_id:
                self.logger.debug(f"💾 流式事件已保存: {event['event_type']} -> {event_id}")

            # 🎯 【新增】自动保存最终结果
            # 检测是否是最终结果事件
            final_event_types = [
                "complete", "result", "final_output", "analysis_complete",
                "generation_complete", "evaluation_complete", "planning_complete"
            ]

            if event.get("event_type") in final_event_types:
                await self._auto_save_final_result(event, user_id, session_id)

        except Exception as e:
            self.logger.error(f"❌ 存储流式事件失败: {e}")

    async def _auto_save_final_result(self, event: Dict[str, Any], user_id: str, session_id: str):
        """
        🆕 自动保存最终结果

        检查Agent是否应该自动保存，如果是则保存最终结果
        """
        try:
            # 检查是否应该自动保存
            if not self._should_auto_save():
                return

            # 获取输出数据
            output_data = event.get("data", "")
            if not output_data:
                return

            # 确定文件类型
            file_type = "json" if isinstance(output_data, dict) else "text"

            # 构建元数据
            metadata = {
                "event_type": event.get("event_type"),
                "event_id": event.get("event_id"),
                "timestamp": event.get("timestamp"),
                "auto_saved": True
            }

            # 使用现有的auto_save_output方法保存
            await self.auto_save_output(
                output_content=output_data,
                user_id=user_id,
                session_id=session_id,
                file_type=file_type,
                metadata=metadata
            )

            self.logger.info(f"✅ {self.agent_name} 最终结果已自动保存")

        except Exception as e:
            self.logger.warning(f"⚠️ 自动保存最终结果失败: {e}")

    def _should_auto_save(self) -> bool:
        """
        🆕 判断是否应该自动保存

        工具类Agent不需要保存，核心Agent需要保存
        """
        # 不需要保存的Agent（工具类）
        utility_agents = [
            "file_reference_agent",
            "websearch_agent",
            "knowledge_agent",
            "text_splitter_agent",
            "text_truncator_agent"
        ]

        # 获取agent的小写名称
        agent_name_lower = self.agent_name.lower()

        # 检查是否是工具类Agent
        for utility in utility_agents:
            if utility in agent_name_lower:
                return False

        # 默认情况下，核心Agent都需要保存
        return True
    
    async def _detect_disconnect(self) -> bool:
        """检测用户是否断网（增强版：优化日志输出）"""
        try:
            # 这里可以实现断网检测逻辑
            # 暂时返回False
            return False
        except Exception as e:
            self.logger.error(f"❌ 断网检测异常: {e}")
            return False
    
    # ==================== 性能优化方法（新增） ====================
    
    def enable_performance_mode(self):
        """
        🚀 开启性能优化模式
        
        关闭思考过程流式输出，显著提升响应速度和用户体验
        适合生产环境或对性能要求较高的场景
        """
        self.enable_thought_streaming = False
        self.logger.info(f"🚀 {self.agent_name} 已开启性能优化模式：思考过程流式输出已关闭")
        
    def enable_debug_mode(self):
        """
        🔍 开启调试模式
        
        开启思考过程流式输出，便于调试和观察AI思考过程
        适合开发环境或需要详细了解AI推理过程的场景
        """
        self.enable_thought_streaming = True
        self.logger.info(f"🔍 {self.agent_name} 已开启调试模式：思考过程流式输出已开启")
    
    async def safe_llm_call(self, user_id: str, session_id: str, messages, **kwargs):
        """安全的LLM调用，自动检查停止状态"""
        # 调用前检查停止状态
        await self.check_and_raise_if_stopped(user_id, session_id, "llm_call")
        
        try:
            # 🧠 【新增】合并agent特定的LLM参数（包括thinking_budget）
            llm_kwargs = self._get_llm_kwargs(**kwargs)
            
            # 执行LLM调用
            if asyncio.iscoroutinefunction(self.llm_client.chat):
                result = await self.llm_client.chat(messages, **llm_kwargs)
            else:
                result = self.llm_client.chat(messages, **llm_kwargs)
            
            # 调用后再次检查停止状态
            await self.check_and_raise_if_stopped(user_id, session_id, "llm_call_complete")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ LLM调用失败: {e}")
            raise
    
    async def safe_stream_call(
        self,
        user_id: str,
        session_id: str,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        安全的流式调用，包含错误处理和多模态处理
        
        Args:
            user_id: 用户ID
            session_id: 会话ID
            messages: 消息列表
            **kwargs: 其他参数
            
        Yields:
            str: 流式响应片段
        """
        # 🛑 调用前检查停止状态
        await self.check_and_raise_if_stopped(user_id, session_id, "stream_call")
        
        try:
            # 🧠 【新增】合并agent特定的LLM参数（包括thinking_budget）
            llm_kwargs = self._get_llm_kwargs(**kwargs)
            
            # 🔧 【性能优化】减少停止状态检查频率，避免过度的Redis查询
            chunk_count = 0
            stop_check_interval = 10  # 每10个chunk检查一次停止状态
            
            # 执行流式调用
            async for chunk in self.llm_client.stream_chat(messages, **llm_kwargs):
                # 🔧 【性能优化】只在特定间隔检查停止状态，减少Redis压力
                chunk_count += 1
                if chunk_count % stop_check_interval == 0:
                    await self.check_and_raise_if_stopped(user_id, session_id, f"stream_chunk_{chunk_count}")
                yield chunk
                    
        except Exception as e:
            self.logger.error(f"❌ {self.agent_name} 流式调用失败: {e}")
            raise
    
    # ==================== Notes系统核心方法（新增） ====================
    
    async def get_notes(self, user_id: str, session_id: str, 
                       note_type: str = None, tags: List[str] = None) -> List[Dict[str, Any]]:
        """获取Notes列表"""
        if not self.notes_manager:
            self.logger.warning("Notes管理器未初始化")
            return []
        
        try:
            notes = await self.notes_manager.get_notes(
                user_id=user_id,
                session_id=session_id,
                note_type=note_type,
                tags=tags
            )
            self.logger.debug(f"✅ 获取Notes成功: {len(notes)}条")
            return notes
        except Exception as e:
            self.logger.error(f"❌ 获取Notes失败: {e}")
            return []
    
    async def resolve_references(self, text: str, user_id: str, session_id: str) -> str:
        """🆕 解析文本中的智能引用"""
        if not self.reference_resolver:
            self.logger.warning("引用解析器未初始化")
            return text
        
        try:
            resolved_text = await self.reference_resolver.resolve_references(
                text=text,
                user_id=user_id,
                session_id=session_id
            )
            self.logger.debug("✅ 智能引用解析成功")
            return resolved_text
        except Exception as e:
            self.logger.error(f"❌ 智能引用解析失败: {e}")
            return text
    
    async def check_stop_state(self, user_id: str, session_id: str) -> bool:
        """🆕 检查停止状态"""
        if not self.stop_manager:
            return False

        try:
            is_stopped = await self.stop_manager.is_stopped(user_id, session_id)
            if is_stopped:
                self.logger.info(f"🛑 检测到停止请求: user_id={user_id}, session_id={session_id}")
            return is_stopped
        except Exception as e:
            self.logger.error(f"❌ 检查停止状态失败: {e}")
            return False
    
    # ==================== 评分分析工具方法（从common_utils整合） ====================
    
    def extract_scores_from_text(self, text: str, score_patterns: Dict[str, str] = None) -> Dict[str, float]:
        """
        从文本中提取评分信息 - 借鉴common_utils设计
        
        Args:
            text: 包含评分的文本
            score_patterns: 评分模式字典
            
        Returns:
            Dict[str, float]: 评分信息字典
        """
        if score_patterns is None:
            score_patterns = {
                "total_score": r"总评分[：:]\s*(\d+\.?\d*)",
                "overall_evaluation": r"总体评价[：:]\s*(\d+\.?\d*)",
                "audience_suitability": r"受众适合度.*?评分[：:]\s*(\d+\.?\d*)",
                "discussion_heat": r"讨论热度.*?评分[：:]\s*(\d+\.?\d*)",
                "scarcity": r"稀缺性.*?评分[：:]\s*(\d+\.?\d*)",
                "playback_data": r"播放数据.*?评分[：:]\s*(\d+\.?\d*)",
                "core_selection": r"核心选点.*?评分[：:]\s*(\d+\.?\d*)",
                "story_concept": r"故事概念.*?评分[：:]\s*(\d+\.?\d*)",
                "story_design": r"故事设计.*?评分[：:]\s*(\d+\.?\d*)",
                "theme_meaning": r"主题立意.*?评分[：:]\s*(\d+\.?\d*)",
                "story_situation": r"故事情境.*?评分[：:]\s*(\d+\.?\d*)",
                "character_setting": r"人物设定.*?评分[：:]\s*(\d+\.?\d*)",
                "character_relationship": r"人物关系.*?评分[：:]\s*(\d+\.?\d*)",
                "plot_bridge": r"情节桥段.*?评分[：:]\s*(\d+\.?\d*)"
            }
        
        import re
        scores = {}
        
        for key, pattern in score_patterns.items():
            match = re.search(pattern, text)
            if match:
                try:
                    scores[key] = float(match.group(1))
                except ValueError:
                    continue
        
        return scores
    
    def calculate_rating_level(self, scores: List[float], total_expected: int = 10) -> str:
        """
        计算评级等级 - 借鉴common_utils设计
        
        Args:
            scores: 评分列表
            total_expected: 预期总轮次
            
        Returns:
            str: 评级等级
        """
        if not scores:
            return "B 普通"
        
        # 过滤有效评分
        valid_scores = [s for s in scores if isinstance(s, (int, float)) and s > 0]
        
        if not valid_scores:
            return "B 普通"
        
        # 统计高分
        high_scores = [s for s in valid_scores if s >= 8.0]
        very_high_scores = [s for s in valid_scores if s >= 8.5]
        
        # 评级逻辑
        if len(valid_scores) != total_expected:
            return "运行失败"
        elif len(very_high_scores) > 0:
            return "S 强烈关注"
        elif len(high_scores) >= 8:
            return "S 强烈关注"
        elif len(high_scores) >= 5:
            return "A 建议关注"
        else:
            return "B 普通"
    
    def generate_analysis_summary(
        self, 
        scores: List[float], 
        attention_level: str, 
        detailed_results: List[Dict[str, Any]]
    ) -> str:
        """
        生成分析摘要 - 借鉴common_utils设计
        
        Args:
            scores: 评分列表
            attention_level: 评级等级
            detailed_results: 详细结果
            
        Returns:
            str: 分析摘要
        """
        valid_scores = [s for s in scores if isinstance(s, (int, float)) and s > 0]
        
        if not valid_scores:
            return "没有有效的评分数据"
        
        # 计算统计指标
        min_score = min(valid_scores)
        max_score = max(valid_scores)
        first_score = valid_scores[0] if valid_scores else 0
        avg = round(sum(valid_scores) / len(valid_scores), 2)
        
        # 计算去除极值的平均分
        if len(valid_scores) > 2:
            sorted_scores = sorted(valid_scores)
            avg_without_extremes = round(
                sum(sorted_scores[1:-1]) / (len(sorted_scores) - 2), 2
            )
        else:
            avg_without_extremes = avg
        
        # 生成摘要
        summary = f"""
# AI评级: {attention_level}
# 结果 
- 评估次数: {len(valid_scores)} 次. 评估结果: {avg_without_extremes if avg_without_extremes else avg}
    - 首次评分 {first_score}
    - 复评分数依次为 {'、'.join([str(x) for x in valid_scores[1:]]) if len(valid_scores) > 1 else '-'}
    - 最高分 {max_score}
    - 最低分 {min_score}
    - 平均分 {avg}
# 评估参考
- 以评估十次为基准：
    - 当出现不及五次8.0及以上评分时，表示该内容 "普通"，对应评级为B。 
    - 当出现至少五次8.0及以上评分时，表示该内容可 "建议关注"，对应评级为A。 
    - 当出现至少八次8.0及以上评分时，表示该内容可 "强烈关注"，对应评级为S。
    - 当出现至少一次8.5及以上评分时，无论其他评分如何，均表示该内容可 "强烈关注"，对应评级为S。
"""
        
        # 添加详细结果
        for i, result in enumerate(detailed_results):
            if isinstance(result, dict) and "text" in result:
                summary += f"\n## 第{i + 1}次执行结果: \n{result['text']}\n"
        
        return summary
    
    def extract_rating_from_analysis(self, analysis: str) -> Optional[str]:
        """
        从分析结果中提取评级 - 借鉴common_utils设计
        
        Args:
            analysis: 分析结果文本
            
        Returns:
            Optional[str]: 评级等级
        """
        import re
        try:
            # 使用正则表达式提取评级信息
            rating_patterns = [
                r"AI评级[：:]\s*([ABC])\s*([^#\n]*)",
                r"评级[：:]\s*([ABC])\s*([^#\n]*)",
                r"等级[：:]\s*([ABC])\s*([^#\n]*)"
            ]
            
            for pattern in rating_patterns:
                match = re.search(pattern, analysis)
                if match:
                    return match.group(1)
            
            # 备选模式
            if "S 强烈关注" in analysis:
                return "S"
            elif "A 建议关注" in analysis:
                return "A"
            elif "B 普通" in analysis:
                return "B"
            
            return None
        except Exception as e:
            self.logger.error(f"提取评级失败: {str(e)}")
            return None
    
    def validate_input_data(self, request_data: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
        """
        验证输入数据 - 借鉴common_utils设计
        
        Args:
            request_data: 请求数据
            required_fields: 必需字段列表
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        missing_fields = []
        for field in required_fields:
            if field not in request_data or not request_data[field]:
                missing_fields.append(field)
        
        if missing_fields:
            return {
                "valid": False,
                "error": f"缺少必需字段: {', '.join(missing_fields)}",
                "missing_fields": missing_fields
            }
        
        return {"valid": True, "error": None}
    
    def format_evaluation_result(
        self, 
        evaluation: str, 
        required_sections: List[str] = None,
        version: str = "2.9"
    ) -> str:
        """
        格式化评估结果 - 借鉴common_utils设计
        
        Args:
            evaluation: 原始评估文本
            required_sections: 必需部分列表
            version: 版本号
            
        Returns:
            str: 格式化后的评估结果
        """
        if required_sections is None:
            required_sections = [
                "【市场潜力】", "【创新属性】", "【内容亮点】", 
                "【总体评价】", "【跟进建议】"
            ]
        
        # 清理文本
        evaluation = evaluation.strip()
        
        # 确保包含版本信息
        if f"【version{version}】" not in evaluation:
            evaluation = f"【version{version}】\n" + evaluation
        
        # 检查缺失部分
        missing_sections = []
        for section in required_sections:
            if section not in evaluation:
                missing_sections.append(section)
        
        if missing_sections:
            self.logger.warning(f"评估结果缺少必要部分: {missing_sections}")
        
        return evaluation
