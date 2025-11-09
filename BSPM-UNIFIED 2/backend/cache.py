"""
GBStudio Automation Hub - Redis Cache Management
Caching, session storage, and rate limiting

Features:
- Connection management with retry logic
- Caching decorators with TTL
- Session storage for horizontal scaling
- Rate limiting storage
- Task queue support (future)
- Health checks and monitoring
"""

import os
import json
import hashlib
from typing import Any, Optional, Callable, Union
from datetime import datetime, timedelta
from functools import wraps
import asyncio

import redis.asyncio as redis
from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import RedisError, ConnectionError, TimeoutError
import structlog

# Logger
logger = structlog.get_logger(__name__)


class RedisManager:
    """Manages Redis connections and operations"""

    def __init__(
        self,
        redis_url: str,
        max_connections: int = 50,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
        retry_on_timeout: bool = True,
        health_check_interval: int = 30,
        decode_responses: bool = True,
    ):
        """
        Initialize Redis manager

        Args:
            redis_url: Redis connection string (redis://[:password@]host:port/db)
            max_connections: Max connections in pool
            socket_timeout: Socket timeout in seconds
            socket_connect_timeout: Connection timeout in seconds
            retry_on_timeout: Retry on timeout
            health_check_interval: Health check interval in seconds
            decode_responses: Decode byte responses to strings
        """
        self.redis_url = redis_url
        self.max_connections = max_connections
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.retry_on_timeout = retry_on_timeout
        self.health_check_interval = health_check_interval
        self.decode_responses = decode_responses

        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[Redis] = None

    def create_pool(self) -> ConnectionPool:
        """Create Redis connection pool"""
        if self._pool:
            return self._pool

        self._pool = ConnectionPool.from_url(
            self.redis_url,
            max_connections=self.max_connections,
            socket_timeout=self.socket_timeout,
            socket_connect_timeout=self.socket_connect_timeout,
            retry_on_timeout=self.retry_on_timeout,
            health_check_interval=self.health_check_interval,
            decode_responses=self.decode_responses,
        )

        logger.info(
            "redis.pool.created",
            max_connections=self.max_connections,
            timeout=self.socket_timeout,
        )

        return self._pool

    def get_client(self) -> Redis:
        """Get Redis client"""
        if not self._client:
            if not self._pool:
                self.create_pool()

            self._client = Redis(connection_pool=self._pool)
            logger.info("redis.client.created")

        return self._client

    async def ping(self) -> bool:
        """Ping Redis server"""
        try:
            client = self.get_client()
            return await client.ping()
        except Exception as e:
            logger.error("redis.ping.failed", error=str(e))
            return False

    async def health_check(self) -> dict:
        """
        Check Redis health

        Returns:
            dict: Health status including connection info and stats
        """
        try:
            start_time = datetime.now()
            client = self.get_client()

            # Ping server
            await client.ping()
            duration = (datetime.now() - start_time).total_seconds()

            # Get server info
            info = await client.info()
            memory_info = {
                "used_memory_human": info.get("used_memory_human"),
                "used_memory_peak_human": info.get("used_memory_peak_human"),
            }

            stats = {
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace_hits": info.get("keyspace_hits"),
                "keyspace_misses": info.get("keyspace_misses"),
            }

            return {
                "status": "healthy",
                "cache": "redis",
                "response_time_seconds": duration,
                "memory": memory_info,
                "stats": stats,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error("redis.health_check.failed", error=str(e))
            return {
                "status": "unhealthy",
                "cache": "redis",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    # ========================================================================
    # Basic Operations
    # ========================================================================

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        try:
            client = self.get_client()
            value = await client.get(key)
            logger.debug("redis.get", key=key, found=value is not None)
            return value
        except Exception as e:
            logger.error("redis.get.error", key=key, error=str(e))
            return None

    async def set(
        self,
        key: str,
        value: str,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to store
            ttl: Time to live in seconds

        Returns:
            bool: Success status
        """
        try:
            client = self.get_client()
            if ttl:
                await client.setex(key, ttl, value)
            else:
                await client.set(key, value)

            logger.debug("redis.set", key=key, ttl=ttl)
            return True
        except Exception as e:
            logger.error("redis.set.error", key=key, error=str(e))
            return False

    async def delete(self, *keys: str) -> int:
        """Delete keys from cache"""
        try:
            client = self.get_client()
            count = await client.delete(*keys)
            logger.debug("redis.delete", keys=keys, count=count)
            return count
        except Exception as e:
            logger.error("redis.delete.error", keys=keys, error=str(e))
            return 0

    async def exists(self, *keys: str) -> int:
        """Check if keys exist"""
        try:
            client = self.get_client()
            count = await client.exists(*keys)
            return count
        except Exception as e:
            logger.error("redis.exists.error", keys=keys, error=str(e))
            return 0

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on key"""
        try:
            client = self.get_client()
            result = await client.expire(key, ttl)
            return result
        except Exception as e:
            logger.error("redis.expire.error", key=key, error=str(e))
            return False

    # ========================================================================
    # JSON Operations
    # ========================================================================

    async def get_json(self, key: str) -> Optional[Any]:
        """Get JSON value from cache"""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError as e:
                logger.error("redis.get_json.decode_error", key=key, error=str(e))
        return None

    async def set_json(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """Set JSON value in cache"""
        try:
            json_value = json.dumps(value)
            return await self.set(key, json_value, ttl)
        except (TypeError, ValueError) as e:
            logger.error("redis.set_json.encode_error", key=key, error=str(e))
            return False

    # ========================================================================
    # Hash Operations
    # ========================================================================

    async def hget(self, name: str, key: str) -> Optional[str]:
        """Get value from hash"""
        try:
            client = self.get_client()
            value = await client.hget(name, key)
            return value
        except Exception as e:
            logger.error("redis.hget.error", name=name, key=key, error=str(e))
            return None

    async def hset(self, name: str, key: str, value: str) -> bool:
        """Set value in hash"""
        try:
            client = self.get_client()
            await client.hset(name, key, value)
            return True
        except Exception as e:
            logger.error("redis.hset.error", name=name, key=key, error=str(e))
            return False

    async def hgetall(self, name: str) -> dict:
        """Get all values from hash"""
        try:
            client = self.get_client()
            data = await client.hgetall(name)
            return data
        except Exception as e:
            logger.error("redis.hgetall.error", name=name, error=str(e))
            return {}

    async def hdel(self, name: str, *keys: str) -> int:
        """Delete keys from hash"""
        try:
            client = self.get_client()
            count = await client.hdel(name, *keys)
            return count
        except Exception as e:
            logger.error("redis.hdel.error", name=name, keys=keys, error=str(e))
            return 0

    # ========================================================================
    # Increment/Decrement Operations
    # ========================================================================

    async def incr(self, key: str, amount: int = 1) -> int:
        """Increment value"""
        try:
            client = self.get_client()
            value = await client.incrby(key, amount)
            return value
        except Exception as e:
            logger.error("redis.incr.error", key=key, error=str(e))
            return 0

    async def decr(self, key: str, amount: int = 1) -> int:
        """Decrement value"""
        try:
            client = self.get_client()
            value = await client.decrby(key, amount)
            return value
        except Exception as e:
            logger.error("redis.decr.error", key=key, error=str(e))
            return 0

    # ========================================================================
    # Session Management
    # ========================================================================

    async def save_session(
        self,
        session_id: str,
        data: dict,
        ttl: int = 86400,  # 24 hours
    ) -> bool:
        """Save user session"""
        key = f"session:{session_id}"
        return await self.set_json(key, data, ttl)

    async def get_session(self, session_id: str) -> Optional[dict]:
        """Get user session"""
        key = f"session:{session_id}"
        return await self.get_json(key)

    async def delete_session(self, session_id: str) -> bool:
        """Delete user session"""
        key = f"session:{session_id}"
        count = await self.delete(key)
        return count > 0

    async def refresh_session(self, session_id: str, ttl: int = 86400) -> bool:
        """Refresh session TTL"""
        key = f"session:{session_id}"
        return await self.expire(key, ttl)

    # ========================================================================
    # Rate Limiting
    # ========================================================================

    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window: int,
    ) -> tuple[bool, int]:
        """
        Check rate limit using sliding window

        Args:
            key: Rate limit key (e.g., "ratelimit:user:123")
            limit: Max requests allowed
            window: Time window in seconds

        Returns:
            tuple: (allowed, remaining_requests)
        """
        try:
            client = self.get_client()
            current_count = await client.get(key)

            if current_count is None:
                # First request in window
                await client.setex(key, window, 1)
                return True, limit - 1
            else:
                count = int(current_count)
                if count < limit:
                    await client.incr(key)
                    return True, limit - count - 1
                else:
                    return False, 0

        except Exception as e:
            logger.error("redis.rate_limit.error", key=key, error=str(e))
            # Allow request on error
            return True, limit

    # ========================================================================
    # Cache Invalidation
    # ========================================================================

    async def invalidate_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        try:
            client = self.get_client()
            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                count = await client.delete(*keys)
                logger.info("redis.invalidate_pattern", pattern=pattern, count=count)
                return count
            return 0

        except Exception as e:
            logger.error("redis.invalidate_pattern.error", pattern=pattern, error=str(e))
            return 0

    async def close(self):
        """Close Redis connections"""
        if self._client:
            await self._client.close()
            logger.info("redis.client.closed")
            self._client = None

        if self._pool:
            await self._pool.disconnect()
            logger.info("redis.pool.closed")
            self._pool = None


# ============================================================================
# Cache Decorators
# ============================================================================

def cache_key_builder(func: Callable, *args, **kwargs) -> str:
    """Build cache key from function name and arguments"""
    key_parts = [func.__module__, func.__name__]

    # Add args
    for arg in args:
        key_parts.append(str(arg))

    # Add kwargs
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}={v}")

    key_string = ":".join(key_parts)
    key_hash = hashlib.md5(key_string.encode()).hexdigest()[:16]

    return f"cache:{func.__name__}:{key_hash}"


def cached(ttl: int = 300, key_builder: Optional[Callable] = None):
    """
    Cache decorator with TTL

    Usage:
        @cached(ttl=300)
        async def expensive_function(param1, param2):
            return result
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = key_builder(func, *args, **kwargs)
            else:
                cache_key = cache_key_builder(func, *args, **kwargs)

            # Try to get from cache
            redis_mgr = get_redis_manager()
            cached_value = await redis_mgr.get_json(cache_key)

            if cached_value is not None:
                logger.debug("cache.hit", key=cache_key)
                return cached_value

            # Cache miss - execute function
            logger.debug("cache.miss", key=cache_key)
            result = await func(*args, **kwargs)

            # Store in cache
            await redis_mgr.set_json(cache_key, result, ttl)

            return result

        return wrapper
    return decorator


# ============================================================================
# Global Redis Manager
# ============================================================================

redis_manager: Optional[RedisManager] = None


def get_redis_manager(
    redis_url: Optional[str] = None,
    max_connections: int = 50,
) -> RedisManager:
    """
    Get or create global Redis manager

    Args:
        redis_url: Redis connection string
        max_connections: Max connections in pool

    Returns:
        RedisManager instance
    """
    global redis_manager

    if redis_manager is None:
        if redis_url is None:
            redis_url = os.getenv(
                "REDIS_URL",
                "redis://:password@redis:6379/0"
            )

        redis_manager = RedisManager(
            redis_url=redis_url,
            max_connections=max_connections,
        )

    return redis_manager
