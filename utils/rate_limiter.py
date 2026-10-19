"""
API限流工具类
基于Redis实现滑动窗口限流算法


"""
import time
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class RateLimiter:
    """基于Redis的API限流器"""

    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.rate_limit_prefix = "rate_limit:"
        self.config_key = "config:rate_limit"
        self.default_config = {
            "limit": 60,
            "window_seconds": 60,
            "enabled": True
        }

    async def _get_redis(self):
        """获取Redis客户端"""
        if self.redis_client:
            return self.redis_client

        try:
            from utils.connection_pool_manager import get_connection_pool_manager
            pool_manager = await get_connection_pool_manager()
            self.redis_client = await pool_manager.get_redis_client('high_priority')
            return self.redis_client
        except Exception as e:
            logger.error(f"获取Redis客户端失败: {e}")
            return None

    async def get_rate_limit_config(self) -> Dict[str, Any]:
        """
        从Redis获取限流配置

        Returns:
            Dict[str, Any]: 限流配置信息
        """
        redis = await self._get_redis()
        if not redis:
            logger.warning("Redis不可用，使用默认限流配置")
            return self.default_config.copy()

        try:
            config_str = await redis.get(self.config_key)
            if config_str:
                import json
                config = json.loads(config_str)
                # 确保必要的字段存在，使用默认值填充缺失的字段
                result = self.default_config.copy()
                result.update(config)
                return result
            else:
                logger.info("Redis中没有找到限流配置，使用默认配置")
                return self.default_config.copy()

        except Exception as e:
            logger.error(f"获取限流配置失败: {e}，使用默认配置")
            return self.default_config.copy()

    async def set_rate_limit_config(
        self,
        limit: int,
        window_seconds: int,
        enabled: bool = True
    ) -> bool:
        """
        设置限流配置到Redis

        Args:
            limit: 限制次数
            window_seconds: 时间窗口
            enabled: 是否启用限流

        Returns:
            bool: 是否设置成功
        """
        redis = await self._get_redis()
        if not redis:
            return False

        try:
            config = {
                "limit": limit,
                "window_seconds": window_seconds,
                "enabled": enabled,
                "updated_at": int(time.time())
            }

            import json
            config_str = json.dumps(config)
            success = await redis.set(self.config_key, config_str)

            if success:
                logger.info(f"限流配置已更新: {config}")

            return success

        except Exception as e:
            logger.error(f"设置限流配置失败: {e}")
            return False

    async def is_allowed(
        self,
        identifier: str,
        limit: Optional[int] = None,
        window_seconds: Optional[int] = None
    ) -> tuple[bool, dict]:
        """
        检查是否允许请求

        Args:
            identifier: 唯一标识符（如用户ID、token等）
            limit: 限制次数（可选，如果不提供则从Redis配置获取）
            window_seconds: 时间窗口（可选，如果不提供则从Redis配置获取）

        Returns:
            tuple[bool, dict]: (是否允许, 限流信息)
            限流信息包含: current_count, limit, window_seconds, reset_time, enabled
        """
        # 首先获取配置
        config = await self.get_rate_limit_config()

        # 如果限流被禁用，直接允许请求
        if not config.get("enabled", True):
            return True, {
                "current_count": 0,
                "limit": config["limit"],
                "window_seconds": config["window_seconds"],
                "reset_time": int(time.time()) + config["window_seconds"],
                "enabled": False,
                "redis_available": True
            }

        # 使用配置中的参数，如果没有传入参数的话
        actual_limit = limit if limit is not None else config["limit"]
        actual_window = window_seconds if window_seconds is not None else config["window_seconds"]

        redis = await self._get_redis()
        if not redis:
            # Redis不可用时，默认允许请求
            logger.warning("Redis不可用，跳过限流检查")
            return True, {
                "current_count": 0,
                "limit": actual_limit,
                "window_seconds": actual_window,
                "reset_time": int(time.time()) + actual_window,
                "enabled": config.get("enabled", True),
                "redis_available": False
            }

        try:
            key = f"{self.rate_limit_prefix}{identifier}"
            current_time = int(time.time())
            window_start = current_time - actual_window

            # 使用Redis sorted set实现滑动窗口
            pipe = redis.pipeline()

            # 移除时间窗口外的记录
            pipe.zremrangebyscore(key, 0, window_start)

            # 获取当前时间窗口内的请求数
            pipe.zcard(key)

            # 添加当前请求
            pipe.zadd(key, {str(current_time): current_time})

            # 设置过期时间
            pipe.expire(key, actual_window)

            results = await pipe.execute()

            current_count = results[1] + 1  # zcard的结果 + 当前请求

            # 计算重置时间（时间窗口结束时间）
            oldest_timestamp = await redis.zrange(key, 0, 0, withscores=True)
            if oldest_timestamp:
                reset_time = int(oldest_timestamp[0][1]) + actual_window
            else:
                reset_time = current_time + actual_window

            is_allowed_result = current_count <= actual_limit

            return is_allowed_result, {
                "current_count": current_count,
                "limit": actual_limit,
                "window_seconds": actual_window,
                "reset_time": reset_time,
                "enabled": config.get("enabled", True),
                "redis_available": True
            }

        except Exception as e:
            logger.error(f"限流检查失败: {e}，默认允许请求")
            return True, {
                "current_count": 0,
                "limit": actual_limit,
                "window_seconds": actual_window,
                "reset_time": int(time.time()) + actual_window,
                "enabled": config.get("enabled", True),
                "redis_available": False,
                "error": str(e)
            }

    async def get_current_usage(self, identifier: str) -> Dict[str, Any]:
        """
        获取当前使用情况

        Args:
            identifier: 唯一标识符

        Returns:
            Dict: 使用情况信息
        """
        redis = await self._get_redis()
        if not redis:
            return {
                "current_count": 0,
                "limit": 0,
                "window_seconds": 0,
                "redis_available": False
            }

        try:
            config = await self.get_rate_limit_config()
            key = f"{self.rate_limit_prefix}{identifier}"
            current_time = int(time.time())
            window_start = current_time - config["window_seconds"]

            # 移除时间窗口外的记录并获取当前计数
            pipe = redis.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            results = await pipe.execute()

            current_count = results[1]

            return {
                "current_count": current_count,
                "limit": config["limit"],
                "window_seconds": config["window_seconds"],
                "remaining": max(0, config["limit"] - current_count),
                "enabled": config.get("enabled", True),
                "redis_available": True
            }

        except Exception as e:
            logger.error(f"获取使用情况失败: {e}")
            return {
                "current_count": 0,
                "limit": 0,
                "window_seconds": 0,
                "redis_available": False,
                "error": str(e)
            }

    async def reset_user_limit(self, identifier: str) -> bool:
        """
        重置用户的限流记录

        Args:
            identifier: 唯一标识符

        Returns:
            bool: 是否重置成功
        """
        redis = await self._get_redis()
        if not redis:
            return False

        try:
            key = f"{self.rate_limit_prefix}{identifier}"
            await redis.delete(key)
            logger.info(f"已重置用户限流记录: {identifier}")
            return True

        except Exception as e:
            logger.error(f"重置限流记录失败: {e}")
            return False


# ==================== 全局实例 ====================

_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter(redis_client=None) -> RateLimiter:
    """获取限流器单例"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(redis_client)
    return _rate_limiter


# ==================== 便捷函数 ====================

async def check_rate_limit(
    identifier: str,
    limit: Optional[int] = None,
    window_seconds: Optional[int] = None
) -> tuple[bool, dict]:
    """
    便捷函数：检查是否允许请求

    Args:
        identifier: 唯一标识符
        limit: 限制次数（可选）
        window_seconds: 时间窗口（可选）

    Returns:
        tuple[bool, dict]: (是否允许, 限流信息)
    """
    limiter = get_rate_limiter()
    return await limiter.is_allowed(identifier, limit, window_seconds)


async def get_user_rate_limit_info(identifier: str) -> Dict[str, Any]:
    """
    便捷函数：获取用户限流信息

    Args:
        identifier: 唯一标识符

    Returns:
        Dict: 限流信息
    """
    limiter = get_rate_limiter()
    return await limiter.get_current_usage(identifier)
