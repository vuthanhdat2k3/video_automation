"""Redis connection pool singleton."""
from redis.asyncio import Redis

from app.config import settings

_pool: Redis | None = None


async def get_redis() -> Redis:
    global _pool
    if _pool is None:
        _pool = Redis.from_url(settings.redis_url, decode_responses=False)
    return _pool


async def close_redis() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None
