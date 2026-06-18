import redis.asyncio as aioredis

from app.core.config import settings

redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Return the shared Redis connection (lazy init)."""
    global redis_client
    if redis_client is None:
        redis_client = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD or None,
            decode_responses=True,
        )
    return redis_client


async def close_redis():
    """Close the Redis connection gracefully."""
    global redis_client
    if redis_client is not None:
        await redis_client.aclose()
        redis_client = None
