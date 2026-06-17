from fastapi import APIRouter

from app.core.redis import get_redis

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check — also pings Redis to verify connectivity."""
    redis_ok = False
    try:
        redis = await get_redis()
        await redis.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    return {"status": "ok", "redis": redis_ok}
