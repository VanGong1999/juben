"""
LLM客户端
支持多种模型提供商，提供统一的LLM调用接口
支持智谱AI免费模型：GLM-4-Flash系列、Cogview、CogVideoX
"""
import os
import json
import logging
import asyncio
import time
import threading
from typing import Dict, Any, List, Optional, AsyncGenerator, Union, Callable
from pathlib import Path
from dotenv import load_dotenv
from enum import Enum
from functools import wraps
from dataclasses import dataclass, field
import aiohttp

try:
    from ..utils.local_model_manager import ensure_ollama_model
except ImportError:
    from utils.local_model_manager import ensure_ollama_model

# 加载环境变量
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)

# 设置日志
logger = logging.getLogger(__name__)

# 连接复用池
_client_pool: Dict[str, "BaseLLMClient"] = {}
_pool_lock = threading.Lock()


def _make_pool_key(provider: str, model: Optional[str], kwargs: Dict[str, Any]) -> str:
    api_key = (
        kwargs.get("api_key")
        or os.getenv("DEEPSEEK_API_KEY")
        or os.getenv("ZHIPU_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or ""
    )
    base_url = kwargs.get("base_url", "")
    temperature = kwargs.get("temperature")
    max_tokens = kwargs.get("max_tokens")
    timeout = kwargs.get("timeout")
    rate_limit = kwargs.get("rate_limit")
    return f"{provider}:{model}:{base_url}:{api_key[:6]}:{temperature}:{max_tokens}:{timeout}:{rate_limit}"


def _default_llm_provider() -> str:
    return (os.getenv("DEFAULT_MODEL_PROVIDER") or "deepseek").strip().lower() or "deepseek"


@dataclass
class StreamChunk:
    """流式响应数据块"""
    content: str
    is_complete: bool = False
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "content": self.content,
            "is_complete": self.is_complete,
            "error": self.error,
            "metadata": self.metadata
        }


@dataclass
class LLMResponse:
    """LLM完整响应"""
    content: str
    model: str
    provider: str
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    finish_reason: Optional[str] = None
    duration: float = 0.0
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "content": self.content,
            "model": self.model,
            "provider": self.provider,
            "total_tokens": self.total_tokens,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "finish_reason": self.finish_reason,
            "duration": self.duration,
            "tool_calls": self.tool_calls,
        }


def _extract_tool_calls_from_message(msg: Any) -> List[Dict[str, Any]]:
    """从 OpenAI-compat message 提取 tool_calls。"""
    tool_calls: List[Dict[str, Any]] = []
    raw = getattr(msg, "tool_calls", None) or []
    for tc in raw:
        fn = getattr(tc, "function", None)
        tool_calls.append(
            {
                "id": getattr(tc, "id", "") or f"call_{uuid_hex()}",
                "type": "function",
                "function": {
                    "name": getattr(fn, "name", "") if fn else "",
                    "arguments": getattr(fn, "arguments", "{}") if fn else "{}",
                },
            }
        )
    return tool_calls


def uuid_hex(n: int = 10) -> str:
    import uuid as _uuid
    return _uuid.uuid4().hex[:n]


def async_retry(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """异步重试装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(f"请求失败，{current_delay}秒后重试 (尝试 {attempt + 1}/{max_retries}): {e}")
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"请求失败，已达最大重试次数 ({max_retries}): {e}")

            raise last_exception

        return wrapper
    return decorator


class ModelType(Enum):
    """模型类型"""
    TEXT = "text"              # 文本生成
    VISION = "vision"          # 视觉理解
    IMAGE_GENERATION = "image_generation"  # 图像生成
    VIDEO_GENERATION = "video_generation"  # 视频生成


class DeepSeekModel:
    """DeepSeek 模型配置（优先便宜的 flash）"""

    TEXT_MODELS = {
        "deepseek-flash": {
            "display_name": "DeepSeek Flash",
            "max_tokens": 1000000,
            "description": "最便宜的主力模型（V4.1 Flash），适合日常创作与工具调用",
            "default": True,
        },
        "deepseek-v4-flash": {
            "display_name": "DeepSeek V4 Flash (兼容名)",
            "max_tokens": 1000000,
            "description": "兼容旧模型名，实际路由到 deepseek-flash 计价",
        },
        "deepseek-chat": {
            "display_name": "DeepSeek Chat (兼容名)",
            "max_tokens": 1000000,
            "description": "兼容旧名，指向 flash 非思考模式；将逐步退役",
        },
        "deepseek-v4-pro": {
            "display_name": "DeepSeek V4 Pro",
            "max_tokens": 1000000,
            "description": "更强推理，成本更高，按需使用",
        },
        "deepseek-reasoner": {
            "display_name": "DeepSeek Reasoner (兼容名)",
            "max_tokens": 1000000,
            "description": "兼容旧推理模型名",
            "thinking_enabled": True,
        },
    }

    @classmethod
    def get_default_model(cls) -> str:
        return os.getenv("DEEPSEEK_MODEL") or "deepseek-flash"

    ALL_MODELS = TEXT_MODELS

    @classmethod
    def get_model(cls, name: str) -> Optional[Dict[str, Any]]:
        return cls.TEXT_MODELS.get(name)


class ZhipuModel:
    """智谱AI模型配置"""

    # 免费文本模型
    TEXT_MODELS = {
        "glm-4-flash": {
            "display_name": "GLM-4-Flash",
            "max_tokens": 128000,
            "description": "快速响应的文本生成模型"
        },
        "glm-4.7-flash": {
            "display_name": "GLM-4.7-Flash",
            "max_tokens": 128000,
            "description": "最新版快速文本生成"
        },
        "glm-4-flash-250414": {
            "display_name": "GLM-4-Flash-250414",
            "max_tokens": 128000,
            "description": "特定版本Flash模型"
        },
        "glm-4.1v-thinking-flash": {
            "display_name": "GLM-4.1V-Thinking-Flash",
            "max_tokens": 128000,
            "description": "带思考链的推理模型",
            "thinking_enabled": True
        }
    }

    # 免费视觉模型
    VISION_MODELS = {
        "glm-4v-flash": {
            "display_name": "GLM-4V-Flash",
            "max_tokens": 8192,
            "description": "视觉理解模型"
        },
        "glm-4.6v-flash": {
            "display_name": "GLM-4.6V-Flash",
            "max_tokens": 8192,
            "description": "最新视觉理解模型"
        }
    }

    # 免费图像生成模型
    IMAGE_MODELS = {
        "cogview-3-flash": {
            "display_name": "Cogview-3-Flash",
            "description": "图像生成模型"
        }
    }

    # 免费视频生成模型
    VIDEO_MODELS = {
        "cogvideox-flash": {
            "display_name": "CogVideoX-Flash",
            "description": "视频生成模型"
        }
    }

    # 所有免费模型
    ALL_FREE_MODELS = {
        **TEXT_MODELS,
        **VISION_MODELS,
        **IMAGE_MODELS,
        **VIDEO_MODELS
    }

    @classmethod
    def get_model(cls, model_name: str) -> Optional[Dict[str, Any]]:
        """获取模型配置"""
        return cls.ALL_FREE_MODELS.get(model_name)

    @classmethod
    def get_models_by_type(cls, model_type: ModelType) -> Dict[str, Dict[str, Any]]:
        """按类型获取模型"""
        if model_type == ModelType.TEXT:
            return cls.TEXT_MODELS
        elif model_type == ModelType.VISION:
            return cls.VISION_MODELS
        elif model_type == ModelType.IMAGE_GENERATION:
            return cls.IMAGE_MODELS
        elif model_type == ModelType.VIDEO_GENERATION:
            return cls.VIDEO_MODELS
        return {}

    @classmethod
    def list_all_models(cls) -> List[str]:
        """列出所有可用模型"""
        return list(cls.ALL_FREE_MODELS.keys())

    @classmethod
    def get_default_model(cls, model_type: ModelType = ModelType.TEXT) -> str:
        """获取默认模型"""
        models = cls.get_models_by_type(model_type)
        if models:
            # Prefer glm-4.7-flash as product default for text
            if model_type == ModelType.TEXT and "glm-4.7-flash" in models:
                return "glm-4.7-flash"
            return list(models.keys())[0]
        return "glm-4.7-flash"


class DashScopeModel:
    """阿里云DashScope模型配置（通义千问系列）"""

    # 文本模型（按价格从低到高排序）
    TEXT_MODELS = {
        "qwen-turbo": {
            "display_name": "Qwen-Turbo",
            "max_tokens": 8192,
            "description": "超高速语言模型，响应速度极快，成本最低",
            "input_price": 0.0003,   # 元/1K tokens
            "output_price": 0.0006   # 元/1K tokens
        },
        "qwen-turbo-latest": {
            "display_name": "Qwen-Turbo-Latest",
            "max_tokens": 8192,
            "description": "最新版本Turbo模型",
            "input_price": 0.0003,
            "output_price": 0.0006
        },
        "qwen-plus": {
            "display_name": "Qwen-Plus",
            "max_tokens": 32768,
            "description": "高性能语言模型，适合复杂任务",
            "input_price": 0.0004,
            "output_price": 0.0006
        },
        "qwen-max": {
            "display_name": "Qwen-Max",
            "max_tokens": 32768,
            "description": "最强效果语言模型，适合最复杂任务",
            "input_price": 0.0012,
            "output_price": 0.0012
        },
        "qwen-long": {
            "display_name": "Qwen-Long",
            "max_tokens": 1000000,
            "description": "超长上下文模型，支持百万token",
            "input_price": 0.0005,
            "output_price": 0.0005
        }
    }

    # 多模态模型
    MULTIMODAL_MODELS = {
        "qwen-vl-plus": {
            "display_name": "Qwen-VL-Plus",
            "max_tokens": 8192,
            "description": "视觉理解多模态模型",
            "input_price": 0.0008,
            "output_price": 0.0008
        },
        "qwen-vl-max": {
            "display_name": "Qwen-VL-Max",
            "max_tokens": 8192,
            "description": "最强视觉理解模型",
            "input_price": 0.0012,
            "output_price": 0.0012
        }
    }

    # 所有模型
    ALL_MODELS = {
        **TEXT_MODELS,
        **MULTIMODAL_MODELS
    }

    @classmethod
    def get_model(cls, model_name: str) -> Optional[Dict[str, Any]]:
        """获取模型配置"""
        return cls.ALL_MODELS.get(model_name)

    @classmethod
    def get_models_by_type(cls, model_type: ModelType) -> Dict[str, Dict[str, Any]]:
        """按类型获取模型"""
        if model_type == ModelType.TEXT:
            return cls.TEXT_MODELS
        elif model_type == ModelType.VISION:
            return cls.MULTIMODAL_MODELS
        return {}

    @classmethod
    def list_all_models(cls) -> List[str]:
        """列出所有可用模型"""
        return list(cls.ALL_MODELS.keys())

    @classmethod
    def get_default_model(cls, model_type: ModelType = ModelType.TEXT) -> str:
        """获取默认模型（最便宜的qwen-turbo）"""
        models = cls.get_models_by_type(model_type)
        if models:
            return list(models.keys())[0]
        return "qwen-turbo"

    @classmethod
    def get_cheapest_model(cls) -> str:
        """获取最便宜的模型"""
        return "qwen-turbo"


class BaseLLMClient:
    """LLM客户端基类"""

    def __init__(self, provider: str, model: str, api_key: str, base_url: str, **kwargs):
        """初始化LLM客户端"""
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.temperature = kwargs.get("temperature", 0.7)
        self.max_tokens = kwargs.get("max_tokens", 4096)
        self.timeout = kwargs.get("timeout", 30)
        self.max_retries = kwargs.get("max_retries", 3)

        # 速率限制保护
        self._request_times = []
        self._rate_limit = kwargs.get("rate_limit", 60)  # 每分钟最多请求数

        self.logger = logger
        self.logger.info(f"初始化LLM客户端: {provider} - {model}")

    async def _check_rate_limit(self):
        """检查速率限制"""
        now = time.time()
        # 清理超过1分钟的记录
        self._request_times = [t for t in self._request_times if now - t < 60]

        if len(self._request_times) >= self._rate_limit:
            sleep_time = 60 - (now - self._request_times[0])
            if sleep_time > 0:
                self.logger.warning(f"达到速率限制，等待 {sleep_time:.1f} 秒")
                await asyncio.sleep(sleep_time)

        self._request_times.append(now)

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """同步聊天接口"""
        raise NotImplementedError("子类必须实现chat方法")

    async def generate(
        self,
        messages: List[Dict[str, str]],
        **kwargs,
    ) -> Dict[str, str]:
        """兼容旧调用：等价 chat 的字典封装，返回 {"content": str}。"""
        content = await self.chat(messages, **kwargs)
        return {"content": content}

    async def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        原生 tool-calling 接口，返回:
        {content, tool_calls, finish_reason, usage}
        OpenAI-compat 子类走 self.client；否则回退纯 chat。

        Prompt-cache：支持 extra_body / prompt_cache_key（OpenClaw 风格稳定路由键）。
        """
        tools = tools or kwargs.pop("tools", None)
        extra_body = kwargs.pop("extra_body", None) or {}
        prompt_cache_key = kwargs.pop("prompt_cache_key", None)
        if prompt_cache_key and "prompt_cache_key" not in extra_body:
            extra_body = dict(extra_body)
            extra_body["prompt_cache_key"] = prompt_cache_key
        for k in ("prompt_cache_retention",):
            if k in kwargs and k not in extra_body:
                extra_body = dict(extra_body)
                extra_body[k] = kwargs.pop(k)

        try:
            from utils.agent_infra.prompt_cache import sort_tools_for_cache, strip_internal_fields

            if tools:
                tools = sort_tools_for_cache(tools)
            messages = strip_internal_fields(messages)
        except Exception:
            pass

        openai_client = getattr(self, "client", None)
        if openai_client is not None and tools and hasattr(openai_client, "chat"):
            model = kwargs.get("model", self.model)
            create_kwargs: Dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": kwargs.get("temperature", self.temperature),
                "tools": tools,
                "tool_choice": kwargs.get("tool_choice", "auto"),
            }
            max_tokens = kwargs.get("max_tokens", self.max_tokens)
            if max_tokens:
                create_kwargs["max_tokens"] = max_tokens
            if extra_body:
                create_kwargs["extra_body"] = extra_body
            # Zhipu 同步客户端特殊处理
            if getattr(self, "_use_openai_compat", True) is False and self.provider == "zhipu":
                # 原生 zhipuai 也可能支持 tools
                create_kwargs["messages"] = (
                    self._convert_messages(messages)
                    if hasattr(self, "_convert_messages")
                    else messages
                )
                create_kwargs.pop("extra_body", None)  # 原生 SDK 可能不认
                response = openai_client.chat.completions.create(**create_kwargs, stream=False)
            else:
                response = await openai_client.chat.completions.create(**create_kwargs)
            msg = response.choices[0].message
            usage = self._normalize_usage(getattr(response, "usage", None))
            tool_calls = _extract_tool_calls_from_message(msg)
            return {
                "content": msg.content or "",
                "tool_calls": tool_calls,
                "finish_reason": response.choices[0].finish_reason or ("tool_calls" if tool_calls else "stop"),
                "usage": usage,
            }

        content = await self.chat(messages, **kwargs)
        return {
            "content": content or "",
            "tool_calls": [],
            "finish_reason": "stop",
            "usage": {},
        }

    @staticmethod
    def _normalize_usage(resp_usage: Any) -> Dict[str, Any]:
        if not resp_usage:
            return {}
        if isinstance(resp_usage, dict):
            raw = dict(resp_usage)
        else:
            raw = {
                "prompt_tokens": getattr(resp_usage, "prompt_tokens", 0) or 0,
                "completion_tokens": getattr(resp_usage, "completion_tokens", 0) or 0,
                "total_tokens": getattr(resp_usage, "total_tokens", 0) or 0,
            }
            ptd = getattr(resp_usage, "prompt_tokens_details", None)
            if ptd is not None:
                raw["prompt_tokens_details"] = {
                    "cached_tokens": getattr(ptd, "cached_tokens", 0) or 0,
                    "cache_write_tokens": getattr(ptd, "cache_write_tokens", 0) or 0,
                }
            for attr in ("cache_read_input_tokens", "cache_creation_input_tokens", "cached_tokens"):
                val = getattr(resp_usage, attr, None)
                if val is not None:
                    raw[attr] = val
        try:
            from utils.agent_infra.prompt_cache import normalize_cache_usage

            raw.update(normalize_cache_usage(raw))
        except Exception:
            pass
        return raw

    async def chat_with_response(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        """聊天接口，返回完整响应对象"""
        start_time = time.time()
        tools = kwargs.pop("tools", None)
        if tools:
            result = await self.chat_with_tools(messages, tools=tools, **kwargs)
            duration = time.time() - start_time
            usage = result.get("usage") or {}
            return LLMResponse(
                content=result.get("content") or "",
                model=self.model,
                provider=self.provider,
                duration=duration,
                tool_calls=list(result.get("tool_calls") or []),
                finish_reason=result.get("finish_reason"),
                prompt_tokens=int(usage.get("prompt_tokens") or 0),
                completion_tokens=int(usage.get("completion_tokens") or 0),
                total_tokens=int(usage.get("total_tokens") or 0),
            )
        content = await self.chat(messages, **kwargs)
        duration = time.time() - start_time

        return LLMResponse(
            content=content,
            model=self.model,
            provider=self.provider,
            duration=duration
        )

    async def stream_chat(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        """流式聊天接口"""
        raise NotImplementedError("子类必须实现stream_chat方法")

    async def stream_chat_with_chunks(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> AsyncGenerator[StreamChunk, None]:
        """流式聊天接口，返回结构化的数据块"""
        try:
            async for content in self.stream_chat(messages, **kwargs):
                if content and not content.startswith("错误:"):
                    yield StreamChunk(content=content, is_complete=False)
                elif content and content.startswith("错误:"):
                    yield StreamChunk(content="", error=content, is_complete=True)
                    return

            # 发送完成标记
            yield StreamChunk(content="", is_complete=True)

        except Exception as e:
            self.logger.error(f"流式聊天失败: {e}")
            yield StreamChunk(content="", error=str(e), is_complete=True)

    async def batch_chat(
        self,
        messages_list: List[List[Dict[str, str]]],
        **kwargs
    ) -> List[str]:
        """批量聊天接口"""
        tasks = [self.chat(messages, **kwargs) for messages in messages_list]
        return await asyncio.gather(*tasks)

    def count_tokens(self, text: str) -> int:
        """估算Token数量（简单实现）"""
        # 中文约1个字符=1个token，英文约4个字符=1个token
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        return chinese_chars + (other_chars // 4)

    def estimate_input_tokens(self, messages: List[Dict[str, str]]) -> int:
        """估算输入Token数量"""
        total = 0
        for msg in messages:
            total += self.count_tokens(msg.get("content", ""))
        return total


class DashScopeLLMClient(BaseLLMClient):
    """阿里云DashScope LLM客户端（通义千问系列）"""

    def __init__(self, model: Optional[str] = None, **kwargs):
        # 默认使用 qwen-turbo（最便宜的模型）
        default_model = DashScopeModel.get_cheapest_model()

        super().__init__(
            provider="dashscope",
            model=model or default_model,
            api_key=kwargs.get("api_key", os.getenv("DASHSCOPE_API_KEY")),
            base_url=kwargs.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            **kwargs
        )

        # 验证模型是否可用
        model_config = DashScopeModel.get_model(self.model)
        if model_config:
            self.logger.info(f"使用DashScope模型: {model_config['display_name']} - {model_config['description']}")
            self.max_tokens = model_config.get("max_tokens", self.max_tokens)
        else:
            self.logger.warning(f"未知模型: {self.model}，将尝试调用")

        try:
            import openai
            self.client = openai.AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            self.logger.info("DashScope客户端初始化成功")
        except ImportError:
            self.logger.error("openai包未安装，请运行: pip install openai")
            raise
        except Exception as e:
            self.logger.error(f"DashScope客户端初始化失败: {e}")
            raise

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """DashScope聊天"""
        try:
            # 支持动态传递model参数
            model = kwargs.get("model", self.model)
            create_kwargs: Dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            }
            if kwargs.get("tools"):
                create_kwargs["tools"] = kwargs["tools"]
                create_kwargs["tool_choice"] = kwargs.get("tool_choice", "auto")

            response = await self.client.chat.completions.create(**create_kwargs)
            msg = response.choices[0].message
            # 若带 tools，调用方应走 chat_with_tools；此处仍返回 content
            return msg.content or ""

        except Exception as e:
            self.logger.error(f"DashScope聊天失败: {e}")
            raise

    async def stream_chat(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        """DashScope流式聊天"""
        try:
            # 支持动态传递model参数
            model = kwargs.get("model", self.model)

            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                stream=True
            )

            async for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            self.logger.error(f"DashScope流式聊天失败: {e}")
            yield f"错误: {str(e)}"


class ZhipuLLMClient(BaseLLMClient):
    """智谱AI LLM客户端 - 支持免费模型"""

    def __init__(self, model: Optional[str] = None, **kwargs):
        # 默认使用 GLM-4.7-Flash
        default_model = ZhipuModel.get_default_model()

        super().__init__(
            provider="zhipu",
            model=model or default_model,
            api_key=kwargs.get("api_key", os.getenv("ZHIPU_API_KEY")),
            base_url=kwargs.get("base_url", "https://open.bigmodel.cn/api/paas/v4"),
            **kwargs
        )

        # 验证模型是否可用
        model_config = ZhipuModel.get_model(self.model)
        if model_config:
            self.logger.info(f"使用免费模型: {model_config['display_name']}")
            self.max_tokens = model_config.get("max_tokens", self.max_tokens)
        else:
            self.logger.warning(f"未知模型: {self.model}，将尝试调用")

        default_base = "https://open.bigmodel.cn/api/paas/v4"
        # 自定义 Base URL 时走 OpenAI 兼容协议（BYOK / 中转）
        self._use_openai_compat = bool(
            self.base_url and self.base_url.rstrip("/") != default_base.rstrip("/")
        )
        try:
            if self._use_openai_compat:
                import openai
                self.client = openai.AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                )
                self.logger.info("智谱AI OpenAI 兼容客户端初始化成功: %s", self.base_url)
            else:
                from zhipuai import ZhipuAI
                self.client = ZhipuAI(api_key=self.api_key)
                self.logger.info("智谱AI客户端初始化成功")
        except ImportError:
            self.logger.error("缺少 zhipuai/openai 包")
            raise
        except Exception as e:
            self.logger.error(f"智谱AI客户端初始化失败: {e}")
            raise

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """智谱AI聊天"""
        try:
            # 转换消息格式
            zhipu_messages = self._convert_messages(messages)

            # 支持动态传递model参数
            model = kwargs.get("model", self.model)

            if self._use_openai_compat:
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=zhipu_messages,
                    temperature=kwargs.get("temperature", self.temperature),
                    max_tokens=kwargs.get("max_tokens", self.max_tokens),
                    stream=False,
                )
            else:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=zhipu_messages,
                    temperature=kwargs.get("temperature", self.temperature),
                    max_tokens=kwargs.get("max_tokens", self.max_tokens),
                    stream=False
                )

            return response.choices[0].message.content

        except Exception as e:
            self.logger.error(f"智谱AI聊天失败: {e}")
            raise

    async def stream_chat(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        """智谱AI流式聊天"""
        try:
            # 转换消息格式
            zhipu_messages = self._convert_messages(messages)

            # 支持动态传递model参数
            model = kwargs.get("model", self.model)

            if self._use_openai_compat:
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=zhipu_messages,
                    temperature=kwargs.get("temperature", self.temperature),
                    max_tokens=kwargs.get("max_tokens", self.max_tokens),
                    stream=True,
                )
                async for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            else:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=zhipu_messages,
                    temperature=kwargs.get("temperature", self.temperature),
                    max_tokens=kwargs.get("max_tokens", self.max_tokens),
                    stream=True
                )

                for chunk in response:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content

        except Exception as e:
            self.logger.error(f"智谱AI流式聊天失败: {e}")
            yield f"错误: {str(e)}"

    def _convert_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        转换消息格式 — 保留 tool / tool_calls，供原生 function calling。
        """
        zhipu_messages: List[Dict[str, Any]] = []
        for msg in messages:
            role = msg.get("role")
            if role in ("system", "user", "assistant"):
                item: Dict[str, Any] = {
                    "role": role,
                    "content": msg.get("content"),
                }
                if msg.get("tool_calls"):
                    item["tool_calls"] = msg["tool_calls"]
                zhipu_messages.append(item)
            elif role == "tool":
                zhipu_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": msg.get("tool_call_id"),
                        "content": msg.get("content") or "",
                    }
                )
            else:
                zhipu_messages.append(
                    {
                        "role": "user",
                        "content": msg.get("content") or "",
                    }
                )
        return zhipu_messages


class OpenRouterLLMClient(BaseLLMClient):
    """OpenRouter LLM客户端"""

    def __init__(self, **kwargs):
        super().__init__(
            provider="openrouter",
            model=kwargs.get("model", "meta-llama/llama-3.3-70b-instruct"),
            api_key=kwargs.get("api_key", os.getenv("OPENROUTER_API_KEY")),
            base_url=kwargs.get("base_url", "https://openrouter.ai/api/v1"),
            **kwargs
        )

        try:
            import openai
            self.client = openai.AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            self.logger.info("OpenRouter客户端初始化成功")
        except ImportError:
            self.logger.error("openai包未安装")
            raise
        except Exception as e:
            self.logger.error(f"OpenRouter客户端初始化失败: {e}")
            raise

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """OpenRouter聊天"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                timeout=kwargs.get("timeout", self.timeout)
            )

            return response.choices[0].message.content

        except Exception as e:
            self.logger.error(f"OpenRouter聊天失败: {e}")
            raise

    async def stream_chat(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        """OpenRouter流式聊天"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                stream=True,
                timeout=kwargs.get("timeout", self.timeout)
            )

            async for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            self.logger.error(f"OpenRouter流式聊天失败: {e}")
            yield f"错误: {str(e)}"


class DeepSeekLLMClient(BaseLLMClient):
    """DeepSeek LLM 客户端（OpenAI 兼容，默认关闭 thinking 以降低成本）"""

    def __init__(self, model: Optional[str] = None, **kwargs):
        default_model = DeepSeekModel.get_default_model()
        model = model or kwargs.pop("model", None) or default_model
        kwargs.pop("model", None)
        super().__init__(
            provider="deepseek",
            model=model,
            api_key=kwargs.pop("api_key", None) or os.getenv("DEEPSEEK_API_KEY"),
            base_url=kwargs.pop("base_url", None)
            or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            **kwargs,
        )
        # 默认关闭思考模式，降低输出 token；推理场景可传 thinking_enabled=True
        self.thinking_enabled = bool(
            kwargs.get(
                "thinking_enabled",
                (DeepSeekModel.get_model(self.model) or {}).get("thinking_enabled", False),
            )
        )
        try:
            import openai

            self.client = openai.AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
            self.logger.info("DeepSeek 客户端初始化成功: %s @ %s", self.model, self.base_url)
        except ImportError:
            self.logger.error("openai 包未安装")
            raise
        except Exception as e:
            self.logger.error(f"DeepSeek 客户端初始化失败: {e}")
            raise

    def _thinking_extra(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        enabled = kwargs.pop("thinking_enabled", None)
        if enabled is None:
            enabled = self.thinking_enabled
        thinking_type = "enabled" if enabled else "disabled"
        extra = dict(kwargs.pop("extra_body", None) or {})
        extra.setdefault("thinking", {"type": thinking_type})
        return extra

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        try:
            model = kwargs.get("model", self.model)
            extra_body = self._thinking_extra(kwargs)
            create_kwargs: Dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "stream": False,
                "extra_body": extra_body,
                "timeout": kwargs.get("timeout", self.timeout),
            }
            if kwargs.get("tools"):
                create_kwargs["tools"] = kwargs["tools"]
                create_kwargs["tool_choice"] = kwargs.get("tool_choice", "auto")
            response = await self.client.chat.completions.create(**create_kwargs)
            return response.choices[0].message.content or ""
        except Exception as e:
            self.logger.error(f"DeepSeek 聊天失败: {e}")
            raise

    async def stream_chat(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        try:
            model = kwargs.get("model", self.model)
            extra_body = self._thinking_extra(kwargs)
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                stream=True,
                extra_body=extra_body,
                timeout=kwargs.get("timeout", self.timeout),
            )
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            self.logger.error(f"DeepSeek 流式聊天失败: {e}")
            yield f"错误: {str(e)}"

    async def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        # 确保 tool 调用也默认关闭 thinking，除非显式开启
        if "extra_body" not in kwargs and "thinking_enabled" not in kwargs:
            kwargs = dict(kwargs)
            kwargs["extra_body"] = self._thinking_extra({})
        elif "thinking_enabled" in kwargs:
            kwargs = dict(kwargs)
            kwargs["extra_body"] = self._thinking_extra(kwargs)
        return await super().chat_with_tools(messages, tools=tools, **kwargs)


class OpenAILLMClient(BaseLLMClient):
    """OpenAI LLM客户端"""

    def __init__(self, **kwargs):
        super().__init__(
            provider="openai",
            model=kwargs.get("model", "gpt-3.5-turbo"),  # 使用最便宜的模型
            api_key=kwargs.get("api_key", os.getenv("OPENAI_API_KEY")),
            base_url=kwargs.get("base_url", "https://api.openai.com/v1"),
            **kwargs
        )

        try:
            import openai
            self.client = openai.AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            self.logger.info("OpenAI客户端初始化成功")
        except ImportError:
            self.logger.error("openai包未安装")
            raise
        except Exception as e:
            self.logger.error(f"OpenAI客户端初始化失败: {e}")
            raise

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """OpenAI聊天"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                timeout=kwargs.get("timeout", self.timeout)
            )

            return response.choices[0].message.content

        except Exception as e:
            self.logger.error(f"OpenAI聊天失败: {e}")
            raise

    async def stream_chat(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        """OpenAI流式聊天"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                stream=True,
                timeout=kwargs.get("timeout", self.timeout)
            )

            async for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            self.logger.error(f"OpenAI流式聊天失败: {e}")
            yield f"错误: {str(e)}"


class LocalLLMClient(BaseLLMClient):
    """本地OpenAI兼容LLM客户端"""

    def __init__(self, **kwargs):
        super().__init__(
            provider="local",
            model=kwargs.get("model", os.getenv("LOCAL_LLM_MODEL", "qwen2.5:7b")),
            api_key=kwargs.get("api_key", os.getenv("LOCAL_LLM_API_KEY", "local")),
            base_url=kwargs.get("base_url", os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:8000/v1")),
            **kwargs
        )

        try:
            import openai
            self.client = openai.AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            self.logger.info("本地OpenAI兼容客户端初始化成功")
        except ImportError:
            self.logger.error("openai包未安装")
            raise
        except Exception as e:
            self.logger.error(f"本地OpenAI兼容客户端初始化失败: {e}")
            raise

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=kwargs.get("model", self.model),
                messages=messages,
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens)
            )
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"本地OpenAI兼容聊天失败: {e}")
            raise

    async def stream_chat(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        try:
            response = await self.client.chat.completions.create(
                model=kwargs.get("model", self.model),
                messages=messages,
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                stream=True
            )
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            self.logger.error(f"本地OpenAI兼容流式聊天失败: {e}")
            yield f"错误: {str(e)}"


class OllamaLLMClient(BaseLLMClient):
    """Ollama本地模型客户端"""

    def __init__(self, **kwargs):
        super().__init__(
            provider="ollama",
            model=kwargs.get("model", os.getenv("OLLAMA_MODEL", "qwen2.5:7b")),
            api_key="",
            base_url=kwargs.get("base_url", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")),
            **kwargs
        )
        auto_pull = os.getenv("OLLAMA_AUTO_PULL", "false").lower() == "true"
        if auto_pull:
            ensure_ollama_model(self.model, self.base_url)

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", self.temperature),
                "num_predict": kwargs.get("max_tokens", self.max_tokens),
            }
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/api/chat", json=payload, timeout=self.timeout) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data.get("message", {}).get("content", "")

    async def stream_chat(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": kwargs.get("temperature", self.temperature),
                "num_predict": kwargs.get("max_tokens", self.max_tokens),
            }
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/api/chat", json=payload, timeout=self.timeout) as resp:
                resp.raise_for_status()
                async for line in resp.content:
                    try:
                        data = json.loads(line.decode("utf-8").strip())
                    except Exception:
                        continue
                    if data.get("done"):
                        break
                    content = data.get("message", {}).get("content")
                    if content:
                        yield content


def get_llm_client(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs
) -> BaseLLMClient:
    """
    获取LLM客户端

    Args:
        provider: 提供商名称 (deepseek/zhipu/dashscope/openrouter/openai/local/ollama)
        model: 模型名称，如果不指定则使用默认便宜模型
        **kwargs: 其他参数

    Returns:
        BaseLLMClient: LLM客户端实例
    """
    try:
        provider = (provider or _default_llm_provider()).strip().lower()

        # 智谱已弃用且未配置 key：回退到默认 provider（deepseek），
        # 避免前端残留的 zhipu 设置 / 历史会话导致「未提供api_key」报错。
        if provider == "zhipu" and not kwargs.get("api_key") and not os.getenv("ZHIPU_API_KEY"):
            fallback = _default_llm_provider()
            logger.warning(f"zhipu 未配置 API key，回退到默认 provider: {fallback}")
            provider = fallback
            model = None

        force_new = kwargs.pop("force_new", False)
        if model is not None:
            kwargs["model"] = model
        resolved_model = kwargs.get("model") or model
        pool_key = _make_pool_key(provider, resolved_model, kwargs)

        if not force_new:
            with _pool_lock:
                cached = _client_pool.get(pool_key)
                if cached:
                    return cached

        if provider == "deepseek":
            client = DeepSeekLLMClient(**kwargs)
        elif provider == "dashscope":
            client = DashScopeLLMClient(**kwargs)
        elif provider == "zhipu":
            client = ZhipuLLMClient(**kwargs)
        elif provider == "openrouter":
            client = OpenRouterLLMClient(**kwargs)
        elif provider == "openai":
            client = OpenAILLMClient(**kwargs)
        elif provider == "local":
            client = LocalLLMClient(**kwargs)
        elif provider == "ollama":
            client = OllamaLLMClient(**kwargs)
        else:
            raise ValueError(f"不支持的LLM提供商: {provider}")

        if not force_new:
            with _pool_lock:
                _client_pool[pool_key] = client

        return client
    except Exception as e:
        logger.error(f"创建LLM客户端失败: {e}")
        raise


def list_available_models(provider: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    列出可用模型

    Args:
        provider: 提供商名称

    Returns:
        List[Dict]: 模型列表
    """
    provider = (provider or _default_llm_provider()).strip().lower()
    if provider == "deepseek":
        return [
            {
                "name": model_name,
                "display_name": config.get("display_name", model_name),
                "description": config.get("description", ""),
                "max_tokens": config.get("max_tokens", 0),
            }
            for model_name, config in DeepSeekModel.ALL_MODELS.items()
        ]
    if provider == "dashscope":
        models = []
        for model_name, config in DashScopeModel.ALL_MODELS.items():
            models.append({
                "name": model_name,
                "display_name": config.get("display_name", model_name),
                "description": config.get("description", ""),
                "max_tokens": config.get("max_tokens", 0)
            })
        return models
    elif provider == "zhipu":
        models = []
        for model_name, config in ZhipuModel.ALL_FREE_MODELS.items():
            models.append({
                "name": model_name,
                "display_name": config.get("display_name", model_name),
                "description": config.get("description", ""),
                "max_tokens": config.get("max_tokens", 0)
            })
        return models
    elif provider == "openai":
        return [
            {
                "name": "gpt-3.5-turbo",
                "display_name": "GPT-3.5 Turbo",
                "description": "最便宜的 OpenAI 模型，性价比高",
                "max_tokens": 16385
            },
            {
                "name": "gpt-4o-mini",
                "display_name": "GPT-4o Mini",
                "description": "经济高效的多模态模型",
                "max_tokens": 128000
            }
        ]
    return []


def get_model_for_purpose(purpose: str) -> str:
    """
    根据用途获取推荐模型

    Args:
        purpose: 用途 (default/reasoning/vision/image_gen/video_gen/latest/cheapest)

    Returns:
        str: 推荐的模型名称
    """
    provider = _default_llm_provider()
    if provider == "deepseek":
        model_mapping = {
            "default": "deepseek-flash",
            "cheapest": "deepseek-flash",
            "latest": "deepseek-flash",
            "reasoning": "deepseek-v4-pro",
            "vision": "deepseek-flash",
            "image_gen": "deepseek-flash",
            "video_gen": "deepseek-flash",
        }
        return model_mapping.get(purpose, "deepseek-flash")

    model_mapping = {
        "default": "qwen-turbo",
        "cheapest": "qwen-turbo",
        "reasoning": "qwen-max",
        "vision": "qwen-vl-plus",
        "latest": "qwen-turbo-latest",
        "image_gen": "qwen-plus",
        "video_gen": "qwen-plus",
    }
    return model_mapping.get(purpose, "qwen-turbo")


if __name__ == "__main__":
    # 测试LLM客户端
    logger.info("=" * 60)
    logger.info("智谱AI 免费模型列表")
    logger.info("=" * 60)

    models = list_available_models("zhipu")
    for model in models:
        logger.info(f"  - {model['display_name']}")
        logger.info(f"    模型ID: {model['name']}")
        logger.info(f"    描述: {model['description']}")
        logger.info("")

    import asyncio

    async def test():
        logger.info("\n测试 GLM-4-Flash 模型:")
        logger.info("-" * 40)

        client = get_llm_client("deepseek", model="deepseek-flash")

        messages = [
            {"role": "system", "content": "你是一个专业的短剧策划助手。"},
            {"role": "user", "content": "请用简短的语言介绍一下你自己。"}
        ]

        response = await client.chat(messages)
        logger.info(f"响应: {response}")

    asyncio.run(test())
