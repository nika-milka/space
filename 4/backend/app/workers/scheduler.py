import asyncio
from datetime import datetime
import pytz
from contextlib import asynccontextmanager

from app.db.session import AsyncSessionLocal
from app.db.repositories import ISSRepository, NASARepository, APODRepository
from app.services.space_service import SpaceDataService
from app.core.config import settings

class Scheduler:
    def __init__(self):
        self.tasks = []
        self.running = False
    
    async def fetch_iss_task(self):
        """Периодическая задача получения позиции МКС"""
        while self.running:
            try:
                async with AsyncSessionLocal() as session:
                    iss_repo = ISSRepository(session)
                    nasa_repo = NASARepository(session)
                    apod_repo = APODRepository(session)
                    
                    service = SpaceDataService(iss_repo, nasa_repo, apod_repo)
                    await service.fetch_and_store_iss_position()
                    
                    print(f"[{datetime.now(pytz.UTC)}] ISS position fetched")
            except Exception as e:
                print(f"Error in ISS task: {e}")
            
            await asyncio.sleep(settings.ISS_EVERY_SECONDS)
    
    async def fetch_apod_task(self):
        """Периодическая задача получения APOD"""
        while self.running:
            try:
                async with AsyncSessionLocal() as session:
                    iss_repo = ISSRepository(session)
                    nasa_repo = NASARepository(session)
                    apod_repo = APODRepository(session)
                    
                    service = SpaceDataService(iss_repo, nasa_repo, apod_repo)
                    await service.fetch_and_store_apod()
                    
                    print(f"[{datetime.now(pytz.UTC)}] APOD fetched")
            except Exception as e:
                print(f"Error in APOD task: {e}")
            
            await asyncio.sleep(settings.APOD_EVERY_SECONDS)
    
    async def fetch_osdr_task(self):
        """Периодическая задача получения данных OSDR"""
        while self.running:
            try:
                async with AsyncSessionLocal() as session:
                    iss_repo = ISSRepository(session)
                    nasa_repo = NASARepository(session)
                    apod_repo = APODRepository(session)
                    
                    service = SpaceDataService(iss_repo, nasa_repo, apod_repo)
                    await service.fetch_and_store_osdr_data()
                    
                    print(f"[{datetime.now(pytz.UTC)}] OSDR data fetched")
            except Exception as e:
                print(f"Error in OSDR task: {e}")
            
            await asyncio.sleep(settings.FETCH_EVERY_SECONDS)
    
    async def start(self):
        """Запуск всех задач"""
        self.running = True
        
        # Запускаем задачи
        self.tasks = [
            asyncio.create_task(self.fetch_iss_task()),
            asyncio.create_task(self.fetch_apod_task()),
            asyncio.create_task(self.fetch_osdr_task())
        ]
        
        print("Scheduler started")
        
        # Ждем завершения всех задач
        await asyncio.gather(*self.tasks, return_exceptions=True)
    
    async def stop(self):
        """Остановка всех задач"""
        self.running = False
        
        # Отменяем все задачи
        for task in self.tasks:
            task.cancel()
        
        # Ждем отмены
        await asyncio.gather(*self.tasks, return_exceptions=True)
        print("Scheduler stopped")

# Глобальный экземпляр планировщика
scheduler = Scheduler()

async def start_scheduler():
    """Запуск планировщика"""
    asyncio.create_task(scheduler.start())

async def stop_scheduler():
    """Остановка планировщика"""
    await scheduler.stop()