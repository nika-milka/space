from typing import List, Optional
from datetime import datetime
import pytz

from app.db.repositories import ISSRepository, NASARepository, APODRepository
from app.clients.external import NASAAPIClient, OSDRClient

class SpaceDataService:
    def __init__(self, iss_repo: ISSRepository, nasa_repo: NASARepository, 
                 apod_repo: APODRepository):
        self.iss_repo = iss_repo
        self.nasa_repo = nasa_repo
        self.apod_repo = apod_repo
        self.nasa_client = NASAAPIClient()
        self.osdr_client = OSDRClient()
    
    async def fetch_and_store_iss_position(self) -> bool:
        """Получаем и сохраняем позицию МКС"""
        try:
            data = await self.nasa_client.get_iss_position()
            if data and data.get("iss_position"):
                position = data["iss_position"]
                
                await self.iss_repo.create_position(
                    latitude=float(position["latitude"]),
                    longitude=float(position["longitude"]),
                    altitude=0,  # API не предоставляет
                    velocity=0,   # API не предоставляет
                    visibility="visible"
                )
                return True
        except Exception as e:
            print(f"Error fetching ISS position: {e}")
        return False
    
    async def fetch_and_store_apod(self) -> bool:
        """Получаем и сохраняем APOD"""
        try:
            data = await self.nasa_client.get_apod()
            if data:
                await self.apod_repo.upsert_apod(
                    date=data.get("date", ""),
                    title=data.get("title", ""),
                    explanation=data.get("explanation", ""),
                    url=data.get("url", ""),
                    hdurl=data.get("hdurl", ""),
                    media_type=data.get("media_type", ""),
                    copyright=data.get("copyright")
                )
                return True
        except Exception as e:
            print(f"Error fetching APOD: {e}")
        return False
    
    async def fetch_and_store_osdr_data(self) -> bool:
        """Получаем и сохраняем данные OSDR"""
        try:
            data = await self.osdr_client.get_datasets(limit=10)
            if data and isinstance(data, list):
                for item in data[:10]:  # Ограничиваем количество
                    await self.nasa_repo.upsert_dataset(
                        dataset_id=item.get("id", ""),
                        title=item.get("title", ""),
                        description=item.get("description", ""),
                        mission=item.get("mission", ""),
                        instrument=item.get("instrument", ""),
                        data_type=item.get("data_type", ""),
                        file_size_mb=item.get("file_size_mb", 0),
                        raw_data=str(item)  # Сохраняем как JSON строку
                    )
                return True
        except Exception as e:
            print(f"Error fetching OSDR data: {e}")
        return False