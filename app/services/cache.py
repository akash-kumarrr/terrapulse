from typing import Callable, Awaitable, TypeVar, Optional
import json
from redis.asyncio import Redis

T = TypeVar("T")

async def get_or_set_cache(
    redis: Redis,
    key: str,
    fetch_func: Callable[[], Awaitable[T]],
    ttl: int = 300
) -> T:
    """
    Get a value from Redis cache.
    If key doesn't exist, execute fetch_func(), store the result in Redis, and return it.
    """
    # 1. Try to get key from Redis
    cached_value = await redis.get(key)
    if cached_value is not None:
        # Assuming JSON stored string data
        return json.loads(cached_value)

    # 2. Key does not exist: Fetch/Compute original data
    data = fetch_func()

    # 3. Store in Redis with TTL (Time-To-Live)
    if data is not None:
        await redis.set(key, json.dumps(data), ex=ttl)

    return json.load(data)