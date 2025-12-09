from fastapi import FastAPI, HTTPException, Request
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import asyncpg
import os
from datetime import datetime
from typing import Optional

from app.middleware.rate_limiter import RateLimiterMiddleware
from app.core.config import settings
# Исправляем импорт - импортируем напрямую из space.py
from app.api.endpoints.space import router as space_router
from app.db.session import init_db

# Конфигурация
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://monouser:monopass@db:5432/monolith")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting Cassiopeia Space API...")
    
    # Инициализация базы данных
    try:
        await init_db()
        print("✅ Database tables initialized")
    except Exception as e:
        print(f"⚠️ Database initialization error: {e}")
        print("⚠️ Continuing without database initialization...")
    
    # Простая проверка соединения с базой данных
    for i in range(3):
        try:
            print(f"🔄 Database connection attempt {i+1}/3...")
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.close()
            print("✅ Database connected successfully")
            break
        except Exception as e:
            print(f"❌ Database connection error: {e}")
            if i < 2:
                await asyncio.sleep(3)
            else:
                print("⚠️ Could not connect to database, some features may be unavailable")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down...")

# Создаем приложение
app = FastAPI(
    title="Кассиопея Space API",
    description="API для мониторинга космических данных",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Добавляем CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене замените на конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Добавляем Rate Limiter middleware
app.add_middleware(
    RateLimiterMiddleware,
    redis_url=settings.REDIS_URL,
    limit=settings.RATE_LIMIT_REQUESTS,
    window=settings.RATE_LIMIT_PERIOD
)

# Включаем роутер space
app.include_router(space_router, prefix="/v1")

@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "message": "Добро пожаловать в Кассиопея Space API",
        "status": "работает",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "space": {
                "iss_positions": "/api/v1/space/iss/positions",
                "nasa_datasets": "/api/v1/space/nasa/datasets",
                "apod": "/api/v1/space/apod",
                "pascal_csv": "/api/v1/space/pascal/csv/stats",
                "stats": "/api/v1/space/stats"
            }
        }
    }

@app.get("/health")
async def health_check():
    """Проверка здоровья"""
    try:
        # Проверяем соединение с базой данных
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Проверяем основные таблицы
        tables = await conn.fetch('''
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_name IN ('iss_positions', 'nasa_datasets', 'apod')
        ''')
        await conn.close()
        
        tables_found = [table['table_name'] for table in tables]
        
        return {
            "status": "healthy",
            "database": "connected",
            "tables_found": tables_found,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "not_connected",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)