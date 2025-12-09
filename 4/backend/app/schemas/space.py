from pydantic import BaseModel, Field
from typing import List, Optional, Generic, TypeVar
from datetime import datetime

T = TypeVar('T')

# Базовые схемы
class ISSPositionResponse(BaseModel):
    id: int
    timestamp: datetime
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    velocity: Optional[float] = None
    visibility: str
    created_at: datetime

class NASADatasetResponse(BaseModel):
    id: int
    dataset_id: str
    title: str
    mission: Optional[str] = None
    instrument: Optional[str] = None
    data_type: Optional[str] = None
    file_size_mb: Optional[float] = None
    fetched_at: datetime

class APODResponse(BaseModel):
    id: int
    date: str
    title: str
    explanation: str
    url: str
    media_type: str
    copyright: Optional[str] = None
    fetched_at: datetime

# Пагинация
class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    limit: int
    pages: int

# Pascal CSV схемы
class PascalCSVItem(BaseModel):
    id: int
    timestamp: str
    boolean_field: str
    numeric_field: float
    text_field: str
    date_field: str
    time_field: str
    category: Optional[str] = None
    status: Optional[str] = None

class PascalCSVResponse(BaseModel):
    data: List[PascalCSVItem]
    count: int
    generated_at: str
    formats: List[str] = ["json", "csv", "html", "excel"]