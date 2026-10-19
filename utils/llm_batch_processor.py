"""
LLM批处理器

支持批量处理LLM请求，提高吞吐量和效率
"""
import asyncio
import time
from typing import List, Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from collections import defaultdict
import hashlib
import json

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import JubenLogger
from utils.llm_client import get_llm_client

logger = JubenLogger("llm_batch_processor")


@dataclass
class BatchRequest:
    """批处理请求"""
    request_id: str
    messages: List[Dict[str, str]]
    kwargs: Dict[str, Any] = field(default_factory=dict)
    model_provider: str = "deepseek"

    def __hash__(self):
        """用于去重的哈希值"""
        content = json.dumps({
            "messages": self.messages,
            "kwargs": self.kwargs,
            "model_provider": self.model_provider
        }, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()


@dataclass
class BatchResult:
    """批处理结果"""
    request_id: str
    result: Optional[str] = None
    error: Optional[Exception] = None
    duration: float = 0.0


@dataclass
class BatchConfig:
    """批处理配置"""
    # 批处理大小
    batch_size: int = 10

    # 批处理超时时间（秒）
    batch_timeout: float = 2.0

    # 最大并发批次数
    max_concurrent_batches: int = 5

    # 是否启用请求去重
    enable_deduplication: bool = True

    # 去重缓存大小
    dedup_cache_size: int = 1000

    # 结果缓存时间（秒）
    result_cache_ttl: int = 3600


class LLMBatchProcessor:
    """
    LLM批处理器

    功能：
    1. 批量合并相似请求
    2. 并发执行多个请求
    3. 请求去重
    4. 结果缓存
    """

    def __init__(self, config: Optional[BatchConfig] = None):
        """
        初始化批处理器

        Args:
            config: 批处理配置
        """
        self.config = config or BatchConfig()

        # 待处理请求队列
        self._pending_requests: List[BatchRequest] = []

        # 请求去重缓存
        self._request_cache: Dict[int, BatchResult] = {}

        # 结果缓存
        self._result_cache: Dict[str, tuple[str, float]] = {}

        # 正在处理的批次
        self._processing_batches: set[str] = set()

        # 信号量控制并发
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_batches)

        # 统计信息
        self._stats = {
            "total_requests": 0,
            "batched_requests": 0,
            "deduped_requests": 0,
            "cache_hits": 0,
            "total_duration": 0.0
        }

        # 批处理任务
        self._batch_task: Optional[asyncio.Task] = None

        logger.info("✅ LLM批处理器初始化完成")

    async def process(
        self,
        messages: List[Dict[str, str]],
        model_provider: str = "deepseek",
        **kwargs
    ) -> str:
        """
        处理单个LLM请求

        Args:
            messages: 消息列表
            model_provider: 模型提供商
            **kwargs: 额外参数

        Returns:
            str: LLM响应
        """
        request = BatchRequest(
            request_id=f"{time.time()}_{id(messages)}",
            messages=messages,
            kwargs=kwargs,
            model_provider=model_provider
        )

        # 检查结果缓存
        cache_key = self._get_cache_key(request)
        if cache_key in self._result_cache:
            result, _ = self._result_cache[cache_key]
            self._stats["cache_hits"] += 1
            logger.debug(f"✅ 缓存命中: {cache_key}")
            return result

        # 检查去重缓存
        request_hash = hash(request)
        if self.config.enable_deduplication and request_hash in self._request_cache:
            self._stats["deduped_requests"] += 1
            logger.debug(f"✅ 请求去重: {request.request_id}")
            cached_result = self._request_cache[request_hash]
            if cached_result.error:
                raise cached_result.error
            return cached_result.result

        # 添加到待处理队列
        self._pending_requests.append(request)
        self._stats["total_requests"] += 1

        # 启动批处理任务
        if self._batch_task is None or self._batch_task.done():
            self._batch_task = asyncio.create_task(self._batch_loop())

        # 等待结果
        return await self._wait_for_result(request)

    async def _wait_for_result(self, request: BatchRequest) -> str:
        """等待请求结果"""
        request_hash = hash(request)
        timeout = self.config.batch_timeout + 30  # 批处理超时 + LLM超时

        start_time = time.time()
        while time.time() - start_time < timeout:
            if request_hash in self._request_cache:
                result = self._request_cache[request_hash]
                if result.error:
                    raise result.error
                return result.result

            await asyncio.sleep(0.01)

        # 超时处理
        if request in self._pending_requests:
            self._pending_requests.remove(request)

        raise TimeoutError(f"请求处理超时: {request.request_id}")

    async def _batch_loop(self):
        """批处理循环"""
        try:
            while self._pending_requests:
                # 获取一批请求
                batch = self._get_next_batch()

                if not batch:
                    await asyncio.sleep(0.01)
                    continue

                # 处理批次
                async with self._semaphore:
                    await self._process_batch(batch)

        except Exception as e:
            logger.error(f"❌ 批处理循环错误: {e}", exc_info=True)

    def _get_next_batch(self) -> List[BatchRequest]:
        """获取下一批请求"""
        if not self._pending_requests:
            return []

        # 按模型提供商分组
        grouped = defaultdict(list)
        for request in self._pending_requests[:self.config.batch_size]:
            grouped[request.model_provider].append(request)

        # 返回第一批
        if grouped:
            first_provider = next(iter(grouped))
            batch = grouped[first_provider]
            # 从待处理队列中移除
            for req in batch:
                if req in self._pending_requests:
                    self._pending_requests.remove(req)
            return batch

        return []

    async def _process_batch(self, batch: List[BatchRequest]):
        """处理一批请求"""
        batch_id = f"batch_{time.time()}_{len(batch)}"
        self._processing_batches.add(batch_id)

        try:
            logger.info(f"🔄 处理批次 {batch_id}: {len(batch)} 个请求")
            self._stats["batched_requests"] += len(batch)

            start_time = time.time()

            # 并发处理所有请求
            tasks = [
                self._process_single_request(req)
                for req in batch
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理结果
            for req, result in zip(batch, results):
                request_hash = hash(req)

                if isinstance(result, Exception):
                    self._request_cache[request_hash] = BatchResult(
                        request_id=req.request_id,
                        error=result
                    )
                else:
                    self._request_cache[request_hash] = BatchResult(
                        request_id=req.request_id,
                        result=result,
                        duration=time.time() - start_time
                    )

                    # 缓存结果
                    cache_key = self._get_cache_key(req)
                    self._result_cache[cache_key] = (result, time.time())

            duration = time.time() - start_time
            self._stats["total_duration"] += duration

            logger.info(
                f"✅ 批次 {batch_id} 完成: "
                f"{len(batch)} 个请求, 耗时 {duration:.2f}s"
            )

        except Exception as e:
            logger.error(f"❌ 批次 {batch_id} 处理失败: {e}", exc_info=True)

        finally:
            self._processing_batches.discard(batch_id)

    async def _process_single_request(self, request: BatchRequest) -> str:
        """处理单个请求"""
        try:
            client = get_llm_client(request.model_provider)
            response = await client.chat(request.messages, **request.kwargs)
            return response

        except Exception as e:
            logger.error(f"❌ 请求 {request.request_id} 失败: {e}")
            raise

    def _get_cache_key(self, request: BatchRequest) -> str:
        """生成缓存键"""
        content = json.dumps({
            "messages": request.messages,
            "kwargs": request.kwargs,
            "model_provider": request.model_provider
        }, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()

    async def cleanup_cache(self):
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self._result_cache.items()
            if current_time - timestamp > self.config.result_cache_ttl
        ]

        for key in expired_keys:
            del self._result_cache[key]

        # 清理请求缓存
        if len(self._request_cache) > self.config.dedup_cache_size:
            # 保留最近的一半
            items_to_keep = list(self._request_cache.items())[
                -self.config.dedup_cache_size // 2:
            ]
            self._request_cache = dict(items_to_keep)

        logger.debug(f"🧹 清理了 {len(expired_keys)} 个过期缓存")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        pending = len(self._pending_requests)
        processing = len(self._processing_batches)

        efficiency = 0
        if self._stats["total_requests"] > 0:
            efficiency = (
                self._stats["batched_requests"] / self._stats["total_requests"]
            )

        avg_duration = 0
        if self._stats["batched_requests"] > 0:
            avg_duration = (
                self._stats["total_duration"] / self._stats["batched_requests"]
            )

        return {
            "pending_requests": pending,
            "processing_batches": processing,
            "cache_size": len(self._result_cache),
            "request_cache_size": len(self._request_cache),
            "statistics": {
                **self._stats,
                "efficiency": round(efficiency, 4),
                "avg_duration": round(avg_duration, 4)
            }
        }

    async def shutdown(self):
        """关闭批处理器"""
        # 等待所有待处理请求完成
        timeout = 30
        start_time = time.time()

        while self._pending_requests and time.time() - start_time < timeout:
            await asyncio.sleep(0.1)

        if self._pending_requests:
            logger.warning(
                f"⚠️ 关闭时仍有 {len(self._pending_requests)} 个待处理请求"
            )

        # 取消批处理任务
        if self._batch_task and not self._batch_task.done():
            self._batch_task.cancel()

        logger.info("✅ LLM批处理器已关闭")


# 全局批处理器实例
_global_batch_processor: Optional[LLMBatchProcessor] = None


def get_batch_processor(config: Optional[BatchConfig] = None) -> LLMBatchProcessor:
    """
    获取全局批处理器实例

    Args:
        config: 批处理配置

    Returns:
        LLMBatchProcessor: 批处理器实例
    """
    global _global_batch_processor

    if _global_batch_processor is None:
        _global_batch_processor = LLMBatchProcessor(config)

        # 启动缓存清理任务
        asyncio.create_task(_cleanup_task())

    return _global_batch_processor


async def _cleanup_task():
    """定期清理缓存"""
    while True:
        try:
            await asyncio.sleep(300)  # 每5分钟清理一次
            if _global_batch_processor:
                await _global_batch_processor.cleanup_cache()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"❌ 缓存清理任务错误: {e}")


# 装饰器
def with_batch_processing(model_provider: str = "deepseek"):
    """
    批处理装饰器

    用法:
    ```python
    @with_batch_processing("zhipu")
    async def generate_text(prompt: str):
        return await llm_client.chat([{"role": "user", "content": prompt}])
    ```
    """
    def decorator(func: Callable[..., Awaitable[str]]) -> Callable[..., Awaitable[str]]:
        async def wrapper(*args, **kwargs) -> str:
            # 提取消息
            messages = kwargs.get("messages")
            if not messages and args:
                messages = args[0]

            if not messages:
                return await func(*args, **kwargs)

            processor = get_batch_processor()
            return await processor.process(
                messages=messages,
                model_provider=model_provider
            )

        return wrapper
    return decorator


if __name__ == "__main__":
    # 测试代码
    async def test_batch_processor():
        """测试批处理器"""
        processor = LLMBatchProcessor(
            BatchConfig(
                batch_size=5,
                batch_timeout=1.0,
                max_concurrent_batches=2
            )
        )

        # 发送多个请求
        tasks = []
        for i in range(20):
            task = processor.process(
                messages=[{"role": "user", "content": f"测试消息 {i+1}"}],
                model_provider="deepseek"
            )
            tasks.append(task)

        # 等待所有请求完成
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 打印统计信息
        stats = processor.get_stats()
        logger.info("\n=== 批处理统计 ===")
        logger.info(json.dumps(stats, indent=2, ensure_ascii=False))

        await processor.shutdown()

    asyncio.run(test_batch_processor())
