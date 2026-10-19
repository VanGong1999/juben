"""
Juben项目Redis客户端管理
支持连接池和三层存储架构
"""
import asyncio
import json
import time
import os
from typing import Optional, Dict, Any, List
from utils.logger import JubenLogger

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    try:
        import aioredis
        REDIS_AVAILABLE = True
    except ImportError:
        REDIS_AVAILABLE = False
        aioredis = None


class RedisConnectionPool:
    """Redis连接池管理器"""
    
    def __init__(self):
        self.logger = JubenLogger("redis_pool")
        self.pools: Dict[str, Any] = {}
        self._initialized = False
        
        # 连接池配置
        self.config = {
            'max_connections': 50,
            'retry_on_timeout': True,
            'socket_connect_timeout': 5,
            'socket_timeout': 5,
            'health_check_interval': 30
        }
    
    async def initialize(self):
        """初始化Redis连接池"""
        if not REDIS_AVAILABLE:
            self.logger.warning("⚠️ Redis不可用，将使用内存模式")
            return
        
        try:
            # Redis配置（优先环境变量）
            host = os.getenv("REDIS_HOST", "localhost")
            port = os.getenv("REDIS_PORT", "6379")
            password = os.getenv("REDIS_PASSWORD", "")
            db = os.getenv("REDIS_DB", "0")

            if password:
                redis_url = f"redis://:{password}@{host}:{port}/{db}"
            else:
                redis_url = f"redis://{host}:{port}/{db}"
            
            # 创建不同优先级的连接池
            priorities = ['high_priority', 'normal_priority', 'low_priority']
            
            for priority in priorities:
                pool = aioredis.ConnectionPool.from_url(
                    redis_url,
                    max_connections=self.config['max_connections'],
                    retry_on_timeout=self.config['retry_on_timeout'],
                    socket_connect_timeout=self.config['socket_connect_timeout'],
                    socket_timeout=self.config['socket_timeout'],
                    health_check_interval=self.config['health_check_interval']
                )
                
                self.pools[priority] = pool
                self.logger.info(f"✅ Redis连接池初始化成功: {priority}")
            
            self._initialized = True
            self.logger.info("✅ Redis连接池管理器初始化完成")
            
        except Exception as e:
            self.logger.error(f"❌ Redis连接池初始化失败: {e}")
            self._initialized = False
    
    async def get_redis_client(self, priority: str = 'normal_priority') -> Optional[Any]:
        """获取Redis客户端"""
        if not self._initialized or not REDIS_AVAILABLE:
            return None
        
        try:
            pool = self.pools.get(priority, self.pools['normal_priority'])
            client = aioredis.Redis(connection_pool=pool)
            
            # 测试连接
            await client.ping()
            return client
            
        except Exception as e:
            self.logger.error(f"❌ 获取Redis客户端失败: {e}")
            return None
    
    async def close_all(self):
        """关闭所有连接池"""
        for priority, pool in self.pools.items():
            try:
                await pool.disconnect()
                self.logger.info(f"✅ Redis连接池已关闭: {priority}")
            except Exception as e:
                self.logger.error(f"❌ 关闭Redis连接池失败: {e}")


# 全局连接池管理器
_connection_pool_manager = None


async def get_connection_pool_manager() -> RedisConnectionPool:
    """获取全局连接池管理器"""
    global _connection_pool_manager
    if _connection_pool_manager is None:
        _connection_pool_manager = RedisConnectionPool()
        await _connection_pool_manager.initialize()
    return _connection_pool_manager


class JubenRedisClient:
    """Juben项目Redis客户端"""
    
    def __init__(self, priority: str = 'normal_priority'):
        self.logger = JubenLogger("juben_redis_client")
        self.priority = priority
        self._client = None
        self._connection_pool_manager = None
    
    async def _get_client(self):
        """获取Redis客户端"""
        if self._client is None:
            if self._connection_pool_manager is None:
                self._connection_pool_manager = await get_connection_pool_manager()
            
            self._client = await self._connection_pool_manager.get_redis_client(self.priority)
            if self._client is None:
                configured_host = os.getenv("REDIS_HOST", "localhost")
                if configured_host == "redis":
                    try:
                        fallback_port = int(os.getenv("REDIS_PORT", "6379"))
                        fallback_password = os.getenv("REDIS_PASSWORD", "")
                        fallback_db = int(os.getenv("REDIS_DB", "0"))
                        self.logger.warning("⚠️ Redis主机 redis 不可达，尝试回退到 localhost")
                        fallback_client = aioredis.Redis(
                            host="localhost",
                            port=fallback_port,
                            password=fallback_password or None,
                            db=fallback_db,
                            socket_connect_timeout=2,
                            socket_timeout=2,
                        )
                        await fallback_client.ping()
                        self._client = fallback_client
                        self.logger.info("✅ Redis已回退连接到 localhost")
                    except Exception as fallback_error:
                        self.logger.error(f"❌ Redis回退 localhost 失败: {fallback_error}")
        
        return self._client
    
    async def set(
        self,
        key: str,
        value: Any,
        expire: int = None,
        nx: bool = False,
        xx: bool = False,
        ex: int = None,
    ) -> bool:
        """设置键值（支持 nx/xx/ex 以兼容分布式锁等场景）"""
        try:
            client = await self._get_client()
            if not client:
                return False

            # 序列化值
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)

            effective_ex = ex if ex is not None else expire
            result = await client.set(key, value, ex=effective_ex, nx=nx, xx=xx)
            return bool(result)

        except Exception as e:
            self.logger.error(f"❌ Redis SET失败: {key}, {e}")
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """获取键值"""
        try:
            client = await self._get_client()
            if not client:
                return None
            
            value = await client.get(key)
            if value is None:
                return None
            
            # 尝试反序列化JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value.decode('utf-8') if isinstance(value, bytes) else value
                
        except Exception as e:
            self.logger.error(f"❌ Redis GET失败: {key}, {e}")
            return None
    
    async def delete(self, key: str) -> bool:
        """删除键"""
        try:
            client = await self._get_client()
            if not client:
                return False
            
            result = await client.delete(key)
            return bool(result)
            
        except Exception as e:
            self.logger.error(f"❌ Redis DELETE失败: {key}, {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            client = await self._get_client()
            if not client:
                return False
            
            result = await client.exists(key)
            return bool(result)
            
        except Exception as e:
            self.logger.error(f"❌ Redis EXISTS失败: {key}, {e}")
            return False
    
    async def expire(self, key: str, seconds: int) -> bool:
        """设置键过期时间"""
        try:
            client = await self._get_client()
            if not client:
                return False
            
            result = await client.expire(key, seconds)
            return bool(result)
            
        except Exception as e:
            self.logger.error(f"❌ Redis EXPIRE失败: {key}, {e}")
            return False
    
    async def hset(self, key: str, field: str, value: Any) -> bool:
        """设置哈希字段"""
        try:
            client = await self._get_client()
            if not client:
                return False
            
            # 序列化值
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            
            result = await client.hset(key, field, value)
            return bool(result)
            
        except Exception as e:
            self.logger.error(f"❌ Redis HSET失败: {key}:{field}, {e}")
            return False
    
    async def hget(self, key: str, field: str) -> Optional[Any]:
        """获取哈希字段"""
        try:
            client = await self._get_client()
            if not client:
                return None
            
            value = await client.hget(key, field)
            if value is None:
                return None
            
            # 尝试反序列化JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value.decode('utf-8') if isinstance(value, bytes) else value
                
        except Exception as e:
            self.logger.error(f"❌ Redis HGET失败: {key}:{field}, {e}")
            return None
    
    async def hgetall(self, key: str) -> Dict[str, Any]:
        """获取所有哈希字段"""
        try:
            client = await self._get_client()
            if not client:
                return {}
            
            result = await client.hgetall(key)
            data = {}
            
            for field, value in result.items():
                # 尝试反序列化JSON
                try:
                    data[field.decode('utf-8')] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    data[field.decode('utf-8')] = value.decode('utf-8') if isinstance(value, bytes) else value
            
            return data
            
        except Exception as e:
            self.logger.error(f"❌ Redis HGETALL失败: {key}, {e}")
            return {}
    
    async def lpush(self, key: str, *values) -> bool:
        """列表左推入"""
        try:
            client = await self._get_client()
            if not client:
                return False
            
            # 序列化值
            serialized_values = []
            for value in values:
                if isinstance(value, (dict, list)):
                    serialized_values.append(json.dumps(value, ensure_ascii=False))
                else:
                    serialized_values.append(str(value))
            
            result = await client.lpush(key, *serialized_values)
            return bool(result)
            
        except Exception as e:
            self.logger.error(f"❌ Redis LPUSH失败: {key}, {e}")
            return False

    async def rpush(self, key: str, *values) -> bool:
        """列表右推入"""
        try:
            client = await self._get_client()
            if not client:
                return False

            serialized_values = []
            for value in values:
                if isinstance(value, (dict, list)):
                    serialized_values.append(json.dumps(value, ensure_ascii=False))
                else:
                    serialized_values.append(str(value))

            result = await client.rpush(key, *serialized_values)
            return bool(result)

        except Exception as e:
            self.logger.error(f"❌ Redis RPUSH失败: {key}, {e}")
            return False
    
    async def lrange(self, key: str, start: int = 0, end: int = -1) -> List[Any]:
        """获取列表范围"""
        try:
            client = await self._get_client()
            if not client:
                return []
            
            result = await client.lrange(key, start, end)
            data = []
            
            for value in result:
                # 尝试反序列化JSON
                try:
                    data.append(json.loads(value))
                except (json.JSONDecodeError, TypeError):
                    data.append(value.decode('utf-8') if isinstance(value, bytes) else value)
            
            return data
            
        except Exception as e:
            self.logger.error(f"❌ Redis LRANGE失败: {key}, {e}")
            return []
    
    async def llen(self, key: str) -> int:
        """获取列表长度"""
        try:
            client = await self._get_client()
            if not client:
                return 0
            
            result = await client.llen(key)
            return int(result)
            
        except Exception as e:
            self.logger.error(f"❌ Redis LLEN失败: {key}, {e}")
            return 0

    async def ltrim(self, key: str, start: int, end: int) -> bool:
        """裁剪列表范围"""
        try:
            client = await self._get_client()
            if not client:
                return False

            result = await client.ltrim(key, start, end)
            return bool(result)

        except Exception as e:
            self.logger.error(f"❌ Redis LTRIM失败: {key}, {e}")
            return False

    async def setex(self, key: str, seconds: int, value: Any) -> bool:
        """设置键值并指定过期时间（兼容接口）"""
        try:
            client = await self._get_client()
            if not client:
                return False

            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)

            result = await client.setex(key, seconds, value)
            return bool(result)

        except Exception as e:
            self.logger.error(f"❌ Redis SETEX失败: {key}, {e}")
            return False
    
    async def ping(self):
        """测试Redis连接"""
        try:
            client = await self._get_client()
            if not client:
                return False
            
            result = await client.ping()
            return result == "PONG"
            
        except Exception as e:
            self.logger.error(f"❌ Redis ping失败: {e}")
            return False
    
    async def close(self):
        """关闭客户端"""
        if self._client:
            try:
                await self._client.close()
                self.logger.info("✅ Redis客户端已关闭")
            except Exception as e:
                self.logger.error(f"❌ 关闭Redis客户端失败: {e}")


# 便捷函数
async def get_redis_client(priority: str = 'normal_priority') -> Optional[JubenRedisClient]:
    """获取Redis客户端实例"""
    if not REDIS_AVAILABLE:
        return None
    
    try:
        client = JubenRedisClient(priority)
        # 测试连接
        await client.ping()
        return client
    except Exception as e:
        logger = JubenLogger("redis_client_factory")
        logger.error(f"❌ 创建Redis客户端失败: {e}")
        return None


async def test_redis_connection() -> bool:
    """测试Redis连接"""
    try:
        client = await get_redis_client()
        if not client:
            return False
        
        # 测试基本操作
        test_key = f"juben_test_{int(time.time())}"
        await client.set(test_key, "test_value", expire=10)
        value = await client.get(test_key)
        await client.delete(test_key)
        
        return value == "test_value"
        
    except Exception as e:
        logger = JubenLogger("redis_test")
        logger.error(f"❌ Redis连接测试失败: {e}")
        return False
