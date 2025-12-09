from fastapi import FastAPI, HTTPException, Request
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import asyncpg
import os
from datetime import datetime
from typing import Optional

# Конфигурация
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://monouser:monopass@db:5432/monolith")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting Cassiopeia Space API...")
    
    # Простая проверка базы данных
    for i in range(3):
        try:
            print(f"🔄 Database connection attempt {i+1}/3...")
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.close()
            print("✅ Database connected successfully")
            break
        except Exception as e:
            print(f"❌ Database error: {e}")
            if i < 2:
                await asyncio.sleep(3)
    
    yield
    
    # Shutdown
    print("🛑 Shutting down...")

# Создаем приложение
app = FastAPI(
    title="Кассиопея Space API",
    version="1.0.0",
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

async def get_db_connection():
    """Получить соединение с БД"""
    try:
        return await asyncpg.connect(DATABASE_URL)
    except Exception as e:
        print(f"❌ DB connection error: {e}")
        return None

# Простой rate limiting без slowapi
_request_timestamps = {}

async def rate_limit_check(request: Request, limit: int = 100, window: int = 60):
    """Простая проверка rate limit"""
    client_ip = request.client.host
    now = datetime.now().timestamp()
    
    if client_ip not in _request_timestamps:
        _request_timestamps[client_ip] = []
    
    # Удаляем старые запросы
    _request_timestamps[client_ip] = [
        ts for ts in _request_timestamps[client_ip] 
        if now - ts < window
    ]
    
    # Проверяем лимит
    if len(_request_timestamps[client_ip]) >= limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Добавляем текущий запрос
    _request_timestamps[client_ip].append(now)

@app.get("/")
async def root(request: Request):
    """Корневой endpoint"""
    await rate_limit_check(request, limit=30)
    
    return {
        "message": "Добро пожаловать в Кассиопея Space API",
        "status": "работает",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "endpoints": [
            "/health - проверка здоровья",
            "/docs - документация API",
            "/api/v1/space/iss/positions - позиции МКС",
            "/api/v1/space/nasa/datasets - датасеты NASA",
            "/api/v1/space/apod - космические фото дня",
            "/api/v1/space/stats - статистика системы"
        ]
    }

@app.get("/health")
async def health_check(request: Request):
    """Проверка здоровья"""
    await rate_limit_check(request, limit=30)
    
    try:
        conn = await get_db_connection()
        if conn:
            # Проверяем таблицы
            tables = await conn.fetch('''
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            ''')
            await conn.close()
            
            return {
                "status": "healthy",
                "database": "connected",
                "tables": len(tables),
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "degraded",
                "database": "not_connected",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/api/v1/space/iss/positions")
async def get_iss_positions(
    request: Request,
    limit: int = 10,
    page: int = 1,
    sort_by: str = "timestamp",
    sort_order: str = "desc"
):
    """Получить позиции МКС"""
    await rate_limit_check(request, limit=60)
    
    try:
        conn = await get_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        # Валидация
        if limit < 1 or limit > 100:
            limit = 10
        if page < 1:
            page = 1
        
        # Проверяем поле сортировки
        valid_sort_fields = ["timestamp", "latitude", "longitude", "created_at"]
        if sort_by not in valid_sort_fields:
            sort_by = "timestamp"
        
        if sort_order not in ["asc", "desc"]:
            sort_order = "desc"
        
        # Подсчет
        total = await conn.fetchval('SELECT COUNT(*) FROM iss_positions')
        
        # Данные
        offset = (page - 1) * limit
        query = f'''
            SELECT id, timestamp, latitude, longitude, altitude, velocity, visibility
            FROM iss_positions 
            ORDER BY {sort_by} {sort_order}
            LIMIT $1 OFFSET $2
        '''
        
        positions = await conn.fetch(query, limit, offset)
        await conn.close()
        
        # Форматирование
        items = []
        for pos in positions:
            items.append({
                "id": pos["id"],
                "timestamp": pos["timestamp"].isoformat() if pos["timestamp"] else None,
                "latitude": float(pos["latitude"]),
                "longitude": float(pos["longitude"]),
                "altitude": float(pos["altitude"]) if pos["altitude"] else 0,
                "velocity": float(pos["velocity"]) if pos["velocity"] else 0,
                "visibility": pos["visibility"]
            })
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": max(1, (total + limit - 1) // limit),
            "sort": {
                "by": sort_by,
                "order": sort_order
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/space/nasa/datasets")
async def get_nasa_datasets(
    request: Request,
    mission: Optional[str] = None,
    limit: int = 10,
    page: int = 1
):
    """Получить датасеты NASA"""
    await rate_limit_check(request, limit=60)
    
    try:
        conn = await get_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        # Валидация
        if limit < 1 or limit > 50:
            limit = 10
        if page < 1:
            page = 1
        
        # Построение запроса
        where_clause = ""
        params = []
        
        if mission:
            where_clause = "WHERE mission = $1"
            params.append(mission)
        
        # Подсчет
        count_query = f"SELECT COUNT(*) FROM nasa_datasets {where_clause}"
        total = await conn.fetchval(count_query, *params)
        
        # Данные
        offset = (page - 1) * limit
        query = f'''
            SELECT id, dataset_id, title, mission, instrument, data_type, file_size_mb, fetched_at
            FROM nasa_datasets 
            {where_clause}
            ORDER BY fetched_at DESC
            LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
        '''
        
        params.extend([limit, offset])
        datasets = await conn.fetch(query, *params)
        await conn.close()
        
        # Форматирование
        items = []
        for ds in datasets:
            items.append({
                "id": ds["id"],
                "dataset_id": ds["dataset_id"],
                "title": ds["title"],
                "mission": ds["mission"],
                "instrument": ds["instrument"],
                "data_type": ds["data_type"],
                "file_size_mb": float(ds["file_size_mb"]) if ds["file_size_mb"] else None,
                "fetched_at": ds["fetched_at"].isoformat() if ds["fetched_at"] else None
            })
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": max(1, (total + limit - 1) // limit),
            "filters": {"mission": mission} if mission else {}
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/space/apod")
async def get_apod(
    request: Request,
    limit: int = 10,
    page: int = 1
):
    """Получить Astronomy Picture of the Day"""
    await rate_limit_check(request, limit=60)
    
    try:
        conn = await get_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        # Валидация
        if limit < 1 or limit > 30:
            limit = 10
        if page < 1:
            page = 1
        
        # Подсчет
        total = await conn.fetchval('SELECT COUNT(*) FROM apod')
        
        # Данные
        offset = (page - 1) * limit
        apods = await conn.fetch('''
            SELECT id, date, title, explanation, url, media_type, copyright, fetched_at
            FROM apod 
            ORDER BY date DESC
            LIMIT $1 OFFSET $2
        ''', limit, offset)
        
        await conn.close()
        
        # Форматирование
        items = []
        for apod in apods:
            items.append({
                "id": apod["id"],
                "date": apod["date"],
                "title": apod["title"],
                "explanation": apod["explanation"],
                "url": apod["url"],
                "media_type": apod["media_type"],
                "copyright": apod["copyright"],
                "fetched_at": apod["fetched_at"].isoformat() if apod["fetched_at"] else None
            })
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": max(1, (total + limit - 1) // limit)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/space/iss/positions")
async def add_iss_position(
    request: Request,
    latitude: float,
    longitude: float,
    altitude: float = 0,
    velocity: float = 0,
    visibility: str = "visible"
):
    """Добавить позицию МКС"""
    await rate_limit_check(request, limit=30)
    
    try:
        conn = await get_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        # Валидация
        if not (-90 <= latitude <= 90):
            raise HTTPException(status_code=400, detail="Latitude must be between -90 and 90")
        if not (-180 <= longitude <= 180):
            raise HTTPException(status_code=400, detail="Longitude must be between -180 and 180")
        
        result = await conn.fetchrow('''
            INSERT INTO iss_positions (latitude, longitude, altitude, velocity, visibility)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, timestamp
        ''', latitude, longitude, altitude, velocity, visibility)
        
        await conn.close()
        
        return {
            "success": True,
            "message": "ISS position added successfully",
            "id": result["id"],
            "timestamp": result["timestamp"].isoformat() if result["timestamp"] else None,
            "data": {
                "latitude": latitude,
                "longitude": longitude,
                "altitude": altitude,
                "velocity": velocity,
                "visibility": visibility
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/space/stats")
async def get_stats(request: Request):
    """Получить статистику"""
    await rate_limit_check(request, limit=30)
    
    try:
        conn = await get_db_connection()
        if not conn:
            return {
                "database": {
                    "iss_positions": 0,
                    "nasa_datasets": 0,
                    "apod_images": 0,
                    "total_records": 0
                },
                "timestamp": datetime.now().isoformat(),
                "note": "Database not available"
            }
        
        # Счетчики
        iss_count = await conn.fetchval('SELECT COUNT(*) FROM iss_positions')
        nasa_count = await conn.fetchval('SELECT COUNT(*) FROM nasa_datasets')
        apod_count = await conn.fetchval('SELECT COUNT(*) FROM apod')
        
        # Последняя позиция
        last_iss = await conn.fetchrow('''
            SELECT timestamp, latitude, longitude 
            FROM iss_positions 
            ORDER BY timestamp DESC 
            LIMIT 1
        ''')
        
        # Последнее APOD
        last_apod = await conn.fetchrow('''
            SELECT date, title 
            FROM apod 
            ORDER BY date DESC 
            LIMIT 1
        ''')
        
        await conn.close()
        
        return {
            "database": {
                "iss_positions": iss_count,
                "nasa_datasets": nasa_count,
                "apod_images": apod_count,
                "total_records": iss_count + nasa_count + apod_count
            },
            "latest": {
                "iss_position": {
                    "timestamp": last_iss["timestamp"].isoformat() if last_iss and last_iss["timestamp"] else None,
                    "latitude": float(last_iss["latitude"]) if last_iss else None,
                    "longitude": float(last_iss["longitude"]) if last_iss else None
                } if last_iss else None,
                "apod": {
                    "date": last_apod["date"] if last_apod else None,
                    "title": last_apod["title"] if last_apod else None
                } if last_apod else None
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)