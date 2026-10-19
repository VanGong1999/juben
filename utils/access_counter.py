"""
访问统计器
基于Redis实现简单的访问次数统计功能

功能：
1. 总访问次数统计
2. 每日访问次数统计
3. 用户访问次数统计
4. 访问趋势分析
5. 独立用户统计


"""

import asyncio
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional


class JubenAccessCounter:
    """剧本平台访问统计器"""

    def __init__(self):
        # 连接池管理器
        self.connection_pool_manager = None
        self.redis_available = False

        # Redis键配置
        self.total_key = "juben:access:total"           # 总访问次数
        self.daily_key_prefix = "juben:access:daily:"   # 每日访问次数
        self.user_key_prefix = "juben:access:user:"     # 用户访问次数
        self.daily_user_key_prefix = "juben:access:daily_user:"  # 每日用户访问次数

        # 数据保留时间
        self.today_ttl_seconds = 86400         # 今日数据：1天过期
        self.recent_ttl_seconds = 86400 * 7    # 近期数据：7天过期
        self.user_ttl_days = 7                 # 用户统计：7天过期

    async def _get_redis_client(self):
        """获取Redis客户端（使用连接池管理器）"""
        if self.connection_pool_manager is None:
            from utils.connection_pool_manager import get_connection_pool_manager
            self.connection_pool_manager = await get_connection_pool_manager()

        # 访问统计属于高优先级操作（统计数据很重要）
        return await self.connection_pool_manager.get_redis_client('high_priority')

    async def _ensure_redis_available(self) -> bool:
        """确保Redis可用（快速检查，避免阻塞主要业务）"""
        try:
            redis_client = await self._get_redis_client()
            raw_client = getattr(redis_client, 'redis', None) or getattr(redis_client, '_redis', None)
            if raw_client:
                # 添加1秒超时，快速失败机制
                import asyncio
                await asyncio.wait_for(raw_client.ping(), timeout=1.0)
                self.redis_available = True
                return True
            else:
                return False
        except asyncio.TimeoutError:
            self.redis_available = False
            return False
        except Exception as e:
            self.redis_available = False
            return False

    async def increment_access(self, user_id: str = None) -> bool:
        """
        增加访问计数

        Args:
            user_id: 用户ID（可选）

        Returns:
            bool: 是否成功记录
        """
        if not await self._ensure_redis_available():
            return False

        try:
            today = date.today().isoformat()  # 格式：2024-01-15

            # 获取Redis客户端并使用pipeline批量执行Redis命令
            redis_client = await self._get_redis_client()
            pipe = redis_client.pipeline()

            # 1. 增加总访问次数
            pipe.incr(self.total_key)

            # 2. 增加今日访问次数
            daily_key = f"{self.daily_key_prefix}{today}"
            pipe.incr(daily_key)
            pipe.expire(daily_key, self.today_ttl_seconds)  # 今日数据：1天过期

            # 3. 如果提供了用户ID，记录用户访问
            if user_id:
                user_key = f"{self.user_key_prefix}{user_id}"
                pipe.incr(user_key)
                pipe.expire(user_key, self.user_ttl_days * 24 * 3600)  # 用户统计：7天过期

                # 4. 记录每日用户访问次数（用于统计每天最活跃用户）
                daily_user_key = f"{self.daily_user_key_prefix}{today}:{user_id}"
                pipe.incr(daily_user_key)
                pipe.expire(daily_user_key, self.today_ttl_seconds)  # 今日用户数据：1天过期

            # 执行所有命令，添加超时控制，避免拖慢主要业务逻辑
            import asyncio
            try:
                # 设置2秒超时，访问统计不应该影响主要业务流程
                await asyncio.wait_for(pipe.execute(), timeout=2.0)
                return True
            except asyncio.TimeoutError:
                return False

        except Exception as e:
            return False

    async def get_total_access(self) -> int:
        """
        获取总访问次数

        Returns:
            int: 总访问次数
        """
        if not await self._ensure_redis_available():
            return 0

        try:
            redis_client = await self._get_redis_client()
            count = await redis_client.get(self.total_key)
            return int(count) if count else 0
        except Exception:
            return 0

    async def get_daily_access(self, target_date: str = None) -> int:
        """
        获取指定日期的访问次数

        Args:
            target_date: 目标日期，格式：YYYY-MM-DD，默认今天

        Returns:
            int: 当日访问次数
        """
        if not await self._ensure_redis_available():
            return 0

        try:
            if not target_date:
                target_date = date.today().isoformat()

            daily_key = f"{self.daily_key_prefix}{target_date}"
            redis_client = await self._get_redis_client()
            count = await redis_client.get(daily_key)
            return int(count) if count else 0
        except Exception:
            return 0

    async def get_user_access(self, user_id: str) -> int:
        """
        获取用户访问次数

        Args:
            user_id: 用户ID

        Returns:
            int: 用户访问次数
        """
        if not await self._ensure_redis_available():
            return 0

        try:
            user_key = f"{self.user_key_prefix}{user_id}"
            redis_client = await self._get_redis_client()
            count = await redis_client.get(user_key)
            return int(count) if count else 0
        except Exception:
            return 0

    async def get_recent_daily_stats(self, days: int = 7) -> Dict[str, int]:
        """
        获取最近几天的访问统计

        Args:
            days: 获取最近多少天的数据

        Returns:
            Dict[str, int]: 日期到访问次数的映射
        """
        if not await self._ensure_redis_available():
            return {}

        try:
            stats = {}
            today = date.today()
            redis_client = await self._get_redis_client()

            for i in range(days):
                target_date = today - timedelta(days=i)
                date_str = target_date.isoformat()
                daily_key = f"{self.daily_key_prefix}{date_str}"

                count = await redis_client.get(daily_key)
                stats[date_str] = int(count) if count else 0

            return stats
        except Exception:
            return {}

    async def get_daily_unique_users(self, target_date: str = None) -> int:
        """
        获取指定日期的独立用户数

        Args:
            target_date: 目标日期，格式：YYYY-MM-DD，默认今天

        Returns:
            int: 独立用户数
        """
        if not await self._ensure_redis_available():
            return 0

        try:
            if not target_date:
                target_date = date.today().isoformat()

            # 查找该日期所有用户的访问记录
            pattern = f"{self.daily_user_key_prefix}{target_date}:*"
            redis_client = await self._get_redis_client()
            keys = await redis_client.keys(pattern)

            # 独立用户数就是key的数量
            return len(keys)
        except Exception:
            return 0

    async def get_stats(self) -> Dict[str, Any]:
        """
        获取所有统计信息

        Returns:
            Dict[str, Any]: 完整的统计信息
        """
        try:
            total = await self.get_total_access()
            today_count = await self.get_daily_access()
            today_users = await self.get_daily_unique_users()
            recent_stats = await self.get_recent_daily_stats(7)

            return {
                "redis_available": self.redis_available,
                "total_access": total,
                "today_access": today_count,
                "today_unique_users": today_users,
                "recent_7_days": recent_stats,
                "status": "healthy" if self.redis_available else "unavailable"
            }
        except Exception as e:
            return {
                "redis_available": False,
                "status": "error",
                "error": str(e)
            }

    async def close(self):
        """关闭连接池管理器"""
        if self.connection_pool_manager:
            self.connection_pool_manager = None
            self.redis_available = False


# ==================== 全局实例 ====================

_access_counter: Optional[JubenAccessCounter] = None


def get_access_counter() -> JubenAccessCounter:
    """获取访问统计器实例（单例）"""
    global _access_counter
    if _access_counter is None:
        _access_counter = JubenAccessCounter()
    return _access_counter


# ==================== 便捷函数 ====================

async def increment_access(user_id: str = None) -> bool:
    """增加访问计数"""
    counter = get_access_counter()
    return await counter.increment_access(user_id)


async def get_access_stats() -> Dict[str, Any]:
    """获取访问统计"""
    counter = get_access_counter()
    return await counter.get_stats()
