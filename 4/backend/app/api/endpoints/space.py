from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.repositories import ISSRepository, NASARepository, APODRepository
from app.schemas.space import (
    ISSPositionResponse, 
    NASADatasetResponse, 
    APODResponse,
    PaginatedResponse
)

router = APIRouter(prefix="/space", tags=["space"])

@router.get("/iss/positions", response_model=PaginatedResponse[ISSPositionResponse])
async def get_iss_positions(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000),
    page: int = Query(1, ge=1)
):
    """Получить позиции МКС"""
    try:
        repo = ISSRepository(db)
        positions = await repo.get_latest_positions(limit=limit)
        
        total = len(positions)
        start = (page - 1) * limit
        end = start + limit
        
        paginated_items = positions[start:end]
        
        return PaginatedResponse(
            items=paginated_items,
            total=total,
            page=page,
            limit=limit,
            pages=(total + limit - 1) // limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/nasa/datasets", response_model=PaginatedResponse[NASADatasetResponse])
async def get_nasa_datasets(
    db: AsyncSession = Depends(get_db),
    mission: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    page: int = Query(1, ge=1)
):
    """Получить датасеты NASA"""
    try:
        repo = NASARepository(db)
        datasets = await repo.get_datasets(mission=mission, limit=1000)  # Больше для пагинации
        
        if mission:
            datasets = [d for d in datasets if d.mission == mission]
        
        total = len(datasets)
        start = (page - 1) * limit
        end = start + limit
        
        paginated_items = datasets[start:end]
        
        return PaginatedResponse(
            items=paginated_items,
            total=total,
            page=page,
            limit=limit,
            pages=(total + limit - 1) // limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/apod", response_model=PaginatedResponse[APODResponse])
async def get_apods(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(30, ge=1, le=100),
    page: int = Query(1, ge=1)
):
    """Получить Astronomy Picture of the Day"""
    try:
        repo = APODRepository(db)
        apods = await repo.get_apods(limit=1000)  # Больше для пагинации
        
        total = len(apods)
        start = (page - 1) * limit
        end = start + limit
        
        paginated_items = apods[start:end]
        
        return PaginatedResponse(
            items=paginated_items,
            total=total,
            page=page,
            limit=limit,
            pages=(total + limit - 1) // limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))