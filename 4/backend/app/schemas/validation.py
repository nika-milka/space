from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

class ISSDataValidation(BaseModel):
    """Валидация данных МКС"""
    latitude: float = Field(..., ge=-90, le=90, description="Широта от -90 до 90")
    longitude: float = Field(..., ge=-180, le=180, description="Долгота от -180 до 180")
    altitude: float = Field(0, ge=0, le=10000, description="Высота от 0 до 10000 км")
    velocity: float = Field(0, ge=0, le=30000, description="Скорость от 0 до 30000 км/ч")
    visibility: str = Field("visible", pattern="^(visible|eclipsed)$")

class NASAFilterValidation(BaseModel):
    """Валидация фильтров NASA"""
    mission: Optional[str] = Field(None, min_length=1, max_length=100)
    instrument: Optional[str] = Field(None, min_length=1, max_length=100)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    
    @validator('start_date', 'end_date')
    def validate_date_format(cls, v):
        if v:
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Дата должна быть в формате YYYY-MM-DD")
        return v

class PaginationValidation(BaseModel):
    """Валидация пагинации"""
    page: int = Field(1, ge=1, le=1000)
    limit: int = Field(10, ge=1, le=100)
    sort_by: Optional[str] = None
    sort_order: str = Field("desc", pattern="^(asc|desc)$")