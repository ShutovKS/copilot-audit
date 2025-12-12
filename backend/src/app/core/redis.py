import redis.asyncio as redis
from src.app.core.config import get_settings

settings = get_settings()

# This client will be used for Pub/Sub operations for real-time logging
redis_client = redis.from_url(settings.CELERY_BROKER_URL, decode_responses=True)
