import logging

from redis import Redis

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

redis_client = Redis.from_url(
    settings.redis_url,
    decode_responses=True,
)


def get_redis_client() -> Redis:
    return redis_client


def check_redis_connection() -> None:
    try:
        redis_client.ping()
        logger.info("Connected to Redis successfully")
    except Exception:
        logger.exception("Failed to connect to Redis")
        raise