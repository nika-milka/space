from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# ЯВНО указываем asyncpg драйвер
DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Создаем асинхронный движок для PostgreSQL
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True
)

# Создаем фабрику сессий
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

async def get_db() -> AsyncSession:
    """
    Dependency для получения асинхронной сессии БД
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    """
    Инициализация базы данных (создание таблиц)
    """
    async with engine.begin() as conn:
        # Импортируем модели здесь, чтобы они были зарегистрированы у Base
        from app.models.domain import ISSPosition, NASADataset, APOD
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created successfully")