from redis.asyncio import Redis, RedisError

from app.core.config import settings

redis_client = Redis.from_url(
    settings.redis_url,
    decode_responses=True,
    health_check_interval=30,
)

async def check_redis_connection() -> bool:
    try:
        return await redis_client.ping()
    except RedisError:
        return False

async def close_redis() -> None:
    await redis_client.aclose()