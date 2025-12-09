import aiohttp
import asyncio
from typing import Optional, Dict, Any
import backoff
from datetime import datetime

from app.core.config import settings

class NASAAPIClient:
    def __init__(self):
        self.base_url = "https://api.nasa.gov"
        self.api_key = settings.NASA_API_KEY
        self.timeout = aiohttp.ClientTimeout(total=30)
    
    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=3
    )
    async def get_iss_position(self) -> Optional[Dict[str, Any]]:
        """Получаем текущую позицию МКС"""
        url = f"{self.base_url}/iss-now.json"
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            headers = {
                "User-Agent": "Cassiopeya-Space-Monitor/1.0",
                "Accept": "application/json"
            }
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                return None
    
    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=3
    )
    async def get_apod(self, date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Astronomy Picture of the Day"""
        url = f"{self.base_url}/planetary/apod"
        
        params = {"api_key": self.api_key}
        if date:
            params["date"] = date
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            headers = {"User-Agent": "Cassiopeya-Space-Monitor/1.0"}
            
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                return None

class OSDRClient:
    def __init__(self):
        self.base_url = settings.NASA_API_URL
        self.timeout = aiohttp.ClientTimeout(total=45)
    
    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=3
    )
    async def get_datasets(self, limit: int = 50) -> Optional[Dict[str, Any]]:
        """Получаем датасеты из OSDR"""
        url = self.base_url
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            headers = {
                "User-Agent": "Cassiopeya-OSDR-Client/1.0",
                "Accept": "application/json"
            }
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                return None