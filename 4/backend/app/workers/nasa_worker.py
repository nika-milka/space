# backend/app/workers/nasa_worker.py
import asyncio
import aiohttp
import asyncpg
import os
from datetime import datetime
from typing import Optional

class NASAWorker:
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL", "postgresql://monouser:monopass@db:5432/monolith")
        self.nasa_api_key = os.getenv("NASA_API_KEY", "")
        self.iss_interval = int(os.getenv("ISS_EVERY_SECONDS", 120))
        self.apod_interval = int(os.getenv("APOD_EVERY_SECONDS", 43200))
        
    async def fetch_iss_position(self):
        """Получить текущую позицию МКС"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('http://api.open-notify.org/iss-now.json', timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        position = data['iss_position']
                        
                        # Сохраняем в базу
                        conn = await asyncpg.connect(self.db_url)
                        await conn.execute('''
                            INSERT INTO iss_positions (latitude, longitude, visibility)
                            VALUES ($1, $2, $3)
                        ''', float(position['latitude']), float(position['longitude']), 'visible')
                        await conn.close()
                        
                        print(f"✅ ISS position fetched: {position}")
                        return True
        except Exception as e:
            print(f"❌ Error fetching ISS: {e}")
        return False
    
    async def fetch_apod(self):
        """Получить Astronomy Picture of the Day"""
        try:
            url = f'https://api.nasa.gov/planetary/apod?api_key={self.nasa_api_key}'
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Сохраняем в базу
                        conn = await asyncpg.connect(self.db_url)
                        await conn.execute('''
                            INSERT INTO apod (date, title, explanation, url, media_type)
                            VALUES ($1, $2, $3, $4, $5)
                            ON CONFLICT (date) DO UPDATE SET
                                title = EXCLUDED.title,
                                explanation = EXCLUDED.explanation,
                                url = EXCLUDED.url,
                                media_type = EXCLUDED.media_type
                        ''', data.get('date'), data.get('title'), 
                             data.get('explanation'), data.get('url'), 
                             data.get('media_type', 'image'))
                        await conn.close()
                        
                        print(f"✅ APOD fetched: {data.get('title')}")
                        return True
        except Exception as e:
            print(f"❌ Error fetching APOD: {e}")
        return False
    
    async def run(self):
        """Запуск фоновых задач"""
        print("🚀 NASA Worker started")
        
        while True:
            try:
                # Получаем позицию МКС
                await self.fetch_iss_position()
                await asyncio.sleep(self.iss_interval)
                
                # Каждые 12 часов получаем APOD
                if datetime.now().hour % 12 == 0:
                    await self.fetch_apod()
                    
            except Exception as e:
                print(f"❌ Worker error: {e}")
                await asyncio.sleep(60)