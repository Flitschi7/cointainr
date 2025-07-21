"""
Cache management endpoints for Cointainr.

This module provides API endpoints for cache statistics and management.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.cache_management import CacheManagementService
from typing import Dict, Any
from app.schemas.cache import CacheStatsSchema, CacheClearResponseSchema

# Create router
router = APIRouter()


def get_cache_service() -> CacheManagementService:
    """
    Dependency for getting the cache management service.
    """
    return CacheManagementService()


@router.get("/conversion/stats", response_model=CacheStatsSchema)
async def get_conversion_cache_stats(
    db: AsyncSession = Depends(get_db),
    cache_service: CacheManagementService = Depends(get_cache_service),
) -> Dict[str, Any]:
    """
    Get statistics about the conversion cache.

    Returns:
        Dict with detailed cache statistics
    """
    try:
        cache_stats = await cache_service.get_cache_stats(db)
        return cache_stats
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get cache statistics: {str(e)}",
        )


@router.post("/clear/prices", response_model=CacheClearResponseSchema)
async def clear_price_cache(
    db: AsyncSession = Depends(get_db),
    cache_service: CacheManagementService = Depends(get_cache_service),
) -> Dict[str, Any]:
    """
    Clear all price cache entries.

    Returns:
        Dict with operation status and count of cleared entries
    """
    try:
        result = await cache_service.clear_price_cache(db)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear price cache: {str(e)}",
        )


@router.post("/clear/conversion", response_model=CacheClearResponseSchema)
async def clear_conversion_cache(
    db: AsyncSession = Depends(get_db),
    cache_service: CacheManagementService = Depends(get_cache_service),
) -> Dict[str, Any]:
    """
    Clear all conversion cache entries.

    Returns:
        Dict with operation status and count of cleared entries
    """
    try:
        result = await cache_service.clear_conversion_cache(db)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear conversion cache: {str(e)}",
        )
