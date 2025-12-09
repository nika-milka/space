from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgres://monouser:monopass@db:5432/monolith"
    
    # NASA API
    NASA_API_KEY: str = "EbF3smROMxhjP1xX9mXxoNTwHyHdlgbQ48YGAebz"
    NASA_API_URL: str = "https://visualization.osdr.nasa.gov/biodata/api/v2/datasets/?format=json"
    
    # Fetch intervals
    ISS_EVERY_SECONDS: int = 120
    APOD_EVERY_SECONDS: int = 43200  # 12 hours
    FETCH_EVERY_SECONDS: int = 300
    
    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    
    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60  # seconds

    class Config:
        env_file = ".env"

settings = Settings()