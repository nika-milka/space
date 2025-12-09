import redis.asyncio as redis
from typing import Optional, Any
import json
from datetime import timedelta

class RedisCacheService:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.client = None
    
    async def connect(self):
        if not self.client:
            self.client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return self.client
    
    async def set_cache(self, key: str, value: Any, ttl: int = 300):
        """Сохранение в кэш"""
        client = await self.connect()
        serialized = json.dumps(value)
        await client.setex(key, ttl, serialized)
    
    async def get_cache(self, key: str) -> Optional[Any]:
        """Получение из кэша"""
        client = await self.connect()
        cached = await client.get(key)
        if cached:
            return json.loads(cached)
        return None
    
    async def invalidate_pattern(self, pattern: str):
        """Инвалидация кэша по паттерну"""
        client = await self.connect()
        keys = await client.keys(pattern)
        if keys:
            await client.delete(*keys)