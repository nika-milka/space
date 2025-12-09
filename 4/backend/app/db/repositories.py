from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from typing import List, Optional
from datetime import datetime
import pytz

from app.models.domain import ISSPosition, NASADataset, APOD

class ISSRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_position(self, latitude: float, longitude: float, altitude: float, 
                            velocity: float, visibility: str) -> ISSPosition:
        position = ISSPosition(
            latitude=latitude,
            longitude=longitude,
            altitude=altitude,
            velocity=velocity,
            visibility=visibility
        )
        self.session.add(position)
        await self.session.commit()
        await self.session.refresh(position)
        return position
    
    async def get_latest_positions(self, limit: int = 100) -> List[ISSPosition]:
        result = await self.session.execute(
            select(ISSPosition)
            .order_by(ISSPosition.timestamp.desc())
            .limit(limit)
        )
        return result.scalars().all()

class NASARepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def upsert_dataset(self, dataset_id: str, **kwargs) -> NASADataset:
        # Проверяем существование
        result = await self.session.execute(
            select(NASADataset).where(NASADataset.dataset_id == dataset_id)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Обновляем существующий
            for key, value in kwargs.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            existing.updated_at = datetime.now(pytz.UTC)
        else:
            # Создаем новый
            existing = NASADataset(dataset_id=dataset_id, **kwargs)
            self.session.add(existing)
        
        await self.session.commit()
        await self.session.refresh(existing)
        return existing
    
    async def get_datasets(self, mission: Optional[str] = None, 
                         limit: int = 50) -> List[NASADataset]:
        query = select(NASADataset)
        if mission:
            query = query.where(NASADataset.mission == mission)
        
        query = query.order_by(NASADataset.fetched_at.desc()).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

class APODRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def upsert_apod(self, date: str, **kwargs) -> APOD:
        result = await self.session.execute(
            select(APOD).where(APOD.date == date)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            for key, value in kwargs.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
        else:
            existing = APOD(date=date, **kwargs)
            self.session.add(existing)
        
        await self.session.commit()
        await self.session.refresh(existing)
        return existing
    
    async def get_apods(self, limit: int = 30) -> List[APOD]:
        result = await self.session.execute(
            select(APOD)
            .order_by(APOD.date.desc())
            .limit(limit)
        )
        return result.scalars().all()