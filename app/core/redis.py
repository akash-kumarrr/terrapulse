from typing import Optional
import redis.asyncio as aioredis
from app.core.config import settings

# Global client reference (Connection Pool wrapper)
redis_client: Optional[aioredis.Redis] = None


async def init_redis() -> None:
    """Initialize the global Redis connection pool."""
    global redis_client
    
    redis_client = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        max_connections=20,  # Prevents exhausting Redis Cloud connections
        socket_timeout=15.0,
        retry_on_timeout=True  # Prevents hanging indefinitely on network issues
    )
    
    # Optional: Verify connection on startup
    await redis_client.ping()


async def close_redis() -> None:
    """Close the global Redis connection pool gracefully."""
    global redis_client
    if redis_client is not None:
        # close() flushes and closes connection pool connections
        await redis_client.aclose()  # Use .aclose() in modern redis-py, or .close()
        redis_client = None


async def get_redis() -> aioredis.Redis:
    """FastAPI dependency to retrieve the active Redis connection client."""
    if redis_client is None:
        raise RuntimeError("Redis client is not initialized. Ensure init_redis() ran during startup.")
    return redis_client

