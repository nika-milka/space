# backend/app/middleware/rate_limiter.py
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as redis
import asyncio
from datetime import datetime, timedelta

class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_url: str, limit: int = 100, window: int = 60):
        super().__init__(app)
        self.redis_url = redis_url
        self.limit = limit
        self.window = window
        self.redis_client = None
    
    async def dispatch(self, request: Request, call_next):
        # Инициализация Redis
        if not self.redis_client:
            self.redis_client = await redis.from_url(
                self.redis_url, 
                encoding="utf-8", 
                decode_responses=True
            )
        
        client_ip = request.client.host
        endpoint = request.url.path
        
        # Ключ для Redis
        key = f"rate_limit:{client_ip}:{endpoint}"
        
        try:
            # Используем Redis для подсчета запросов
            current = await self.redis_client.get(key)
            
            if current is None:
                # Первый запрос в окне
                await self.redis_client.setex(key, self.window, 1)
                current = 1
            else:
                current = int(current)
                if current >= self.limit:
                    raise HTTPException(
                        status_code=429, 
                        detail="Rate limit exceeded. Please try again later."
                    )
                await self.redis_client.incr(key)
            
            # Добавляем заголовки с информацией о лимите
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(self.limit)
            response.headers["X-RateLimit-Remaining"] = str(self.limit - current)
            
            return response
            
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            # В случае ошибки Redis пропускаем rate limiting
            return await call_next(request)