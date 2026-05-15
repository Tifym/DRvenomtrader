"""
Dr. Venom Trader - Redis Connection Manager
Provides async Redis client for caching and pub/sub.
"""

import redis.asyncio as aioredis
from app.config import settings


class RedisManager:
    """Manages async Redis connections for the application."""

    _client: aioredis.Redis | None = None

    @classmethod
    async def connect(cls) -> aioredis.Redis:
        """Initialize and return the Redis client."""
        if cls._client is None:
            cls._client = aioredis.from_url(
                settings.redis_url,
                decode_responses=True,
                max_connections=20,
            )
            # Verify connection
            await cls._client.ping()
        return cls._client

    @classmethod
    async def get_client(cls) -> aioredis.Redis:
        """Get the active Redis client. Connect if needed."""
        if cls._client is None:
            return await cls.connect()
        return cls._client

    @classmethod
    async def disconnect(cls) -> None:
        """Close the Redis connection."""
        if cls._client is not None:
            await cls._client.close()
            cls._client = None
