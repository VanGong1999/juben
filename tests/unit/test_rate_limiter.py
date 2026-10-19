"""
Unit tests for RateLimiter utility

Tests the rate limiting functionality without Redis dependency
"""
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from collections import OrderedDict


@pytest.mark.unit
class TestRateLimiter:
    """Test rate limiter functionality"""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client"""
        redis = AsyncMock()
        # pipeline() 在 redis-py 中是同步方法，返回同步的 pipeline 对象
        redis.pipeline = MagicMock(return_value=redis)
        redis.execute.return_value = None
        redis.get.return_value = None
        redis.set.return_value = True
        redis.delete.return_value = 1
        redis.keys.return_value = []
        redis.zcard.return_value = 0
        redis.zadd.return_value = 1
        redis.zremrangebyscore.return_value = 0
        redis.zrange.return_value = []
        redis.expire.return_value = True
        return redis

    @pytest.fixture
    def rate_limiter(self, mock_redis):
        """Create rate limiter with mocked Redis"""
        from utils.rate_limiter import RateLimiter
        limiter = RateLimiter(redis_client=mock_redis)
        return limiter

    def test_init(self):
        """Test rate limiter initialization"""
        from utils.rate_limiter import RateLimiter

        limiter = RateLimiter()
        assert limiter.rate_limit_prefix == "rate_limit:"
        assert limiter.config_key == "config:rate_limit"
        assert limiter.default_config["limit"] == 60
        assert limiter.default_config["window_seconds"] == 60

    @pytest.mark.asyncio
    async def test_get_rate_limit_config_with_redis(self, rate_limiter, mock_redis):
        """Test getting config from Redis"""
        mock_config = '{"limit": 100, "window_seconds": 60, "enabled": true}'
        mock_redis.get.return_value = mock_config

        config = await rate_limiter.get_rate_limit_config()

        assert config["limit"] == 100
        assert config["window_seconds"] == 60
        assert config["enabled"] is True

    @pytest.mark.asyncio
    async def test_get_rate_limit_config_default(self, rate_limiter, mock_redis):
        """Test getting default config when Redis unavailable"""
        mock_redis.get.return_value = None

        config = await rate_limiter.get_rate_limit_config()

        assert config["limit"] == 60
        assert config["window_seconds"] == 60
        assert config["enabled"] is True

    @pytest.mark.asyncio
    async def test_set_rate_limit_config(self, rate_limiter, mock_redis):
        """Test setting rate limit config"""
        success = await rate_limiter.set_rate_limit_config(
            limit=100,
            window_seconds=120,
            enabled=True
        )

        assert success is True
        mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_allowed_when_disabled(self, rate_limiter):
        """Test is_allowed returns True when rate limiting disabled"""
        with patch.object(rate_limiter, 'get_rate_limit_config') as mock_config:
            mock_config.return_value = {"enabled": False, "limit": 60, "window_seconds": 60}

            allowed, info = await rate_limiter.is_allowed("user_123")

            assert allowed is True
            assert info["enabled"] is False

    @pytest.mark.asyncio
    async def test_is_allowed_under_limit(self, rate_limiter, mock_redis):
        """Test is_allowed returns True when under limit"""
        # Mock pipeline responses
        mock_redis.execute.return_value = [None, 5, 1, True]  # 5 requests in window
        mock_redis.zrange.return_value = []

        allowed, info = await rate_limiter.is_allowed("user_123", limit=10)

        assert allowed is True
        assert info["current_count"] == 6  # 5 existing + 1 new

    @pytest.mark.asyncio
    async def test_is_allowed_over_limit(self, rate_limiter, mock_redis):
        """Test is_allowed returns False when over limit"""
        # Mock pipeline responses
        mock_redis.execute.return_value = [None, 10, 1, True]  # Already at limit
        mock_redis.zrange.return_value = []

        allowed, info = await rate_limiter.is_allowed("user_123", limit=10)

        assert allowed is False
        assert info["current_count"] == 11

    @pytest.mark.asyncio
    async def test_get_current_usage(self, rate_limiter, mock_redis):
        """Test getting current usage statistics"""
        mock_redis.execute.return_value = [None, 5]

        with patch.object(rate_limiter, 'get_rate_limit_config') as mock_config:
            mock_config.return_value = {"limit": 60, "window_seconds": 60, "enabled": True}

            usage = await rate_limiter.get_current_usage("user_123")

            assert usage["current_count"] == 5
            assert usage["limit"] == 60
            assert "remaining" in usage

    @pytest.mark.asyncio
    async def test_reset_user_limit(self, rate_limiter, mock_redis):
        """Test resetting user rate limit"""
        mock_redis.delete.return_value = 1

        success = await rate_limiter.reset_user_limit("user_123")

        assert success is True
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_allowed_without_redis(self, rate_limiter):
        """Test is_allowed when Redis unavailable"""
        with patch.object(rate_limiter, '_get_redis', return_value=None):
            allowed, info = await rate_limiter.is_allowed("user_123")

            assert allowed is True
            assert info["redis_available"] is False


@pytest.mark.unit
class TestRateLimiterHelpers:
    """Test rate limiter helper functions"""

    def test_get_rate_limiter_singleton(self):
        """Test get_rate_limiter returns singleton"""
        from utils.rate_limiter import get_rate_limiter, _rate_limiter

        # Reset global
        import utils.rate_limiter
        utils.rate_limiter._rate_limiter = None

        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()

        assert limiter1 is limiter2

    @pytest.mark.asyncio
    async def test_check_rate_limit_function(self):
        """Test check_rate_limit convenience function"""
        from utils.rate_limiter import check_rate_limit

        with patch('utils.rate_limiter.get_rate_limiter') as mock_get:
            mock_limiter = AsyncMock()
            mock_limiter.is_allowed.return_value = (True, {"current_count": 5})
            mock_get.return_value = mock_limiter

            allowed, info = await check_rate_limit("user_123")

            assert allowed is True
            mock_limiter.is_allowed.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_rate_limit_info_function(self):
        """Test get_user_rate_limit_info convenience function"""
        from utils.rate_limiter import get_user_rate_limit_info

        with patch('utils.rate_limiter.get_rate_limiter') as mock_get:
            mock_limiter = AsyncMock()
            mock_limiter.get_current_usage.return_value = {"current_count": 5}
            mock_get.return_value = mock_limiter

            info = await get_user_rate_limit_info("user_123")

            assert info["current_count"] == 5
