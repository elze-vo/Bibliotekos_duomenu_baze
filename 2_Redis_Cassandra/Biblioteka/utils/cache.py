import redis
from Biblioteka.config import REDIS_URL

redis_client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True
)

def get_cache(key):
    """Retrieve value from cache"""
    return redis_client.get(key)

def set_cache(key, value, ttl=None):
    """
    Store value in cache with optional TTL (in seconds)
    :param key: cache key
    :param value: value to store (string)
    :param ttl: time-to-live in seconds (None = no expiration)
    """
    if ttl:
        redis_client.setex(key, ttl, value)
    else:
        redis_client.set(key, value)

def delete_cache(key):
    """
    Delete a key from cache
    :param key: cache key to delete
    """
    redis_client.delete(key)