"""
Conversion endpoints for Cointainr.

This module provides API endpoints for currency conversion operations.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.conversion_service import ConversionService
from typing import Dict, Any
from app.schemas.conversion import ConversionRateSchema

# Create router
router = APIRouter()


def get_conversion_service() -> ConversionService:
    """
    Dependency for getting the conversion service.
    """
    return ConversionService()


@router.get("/rate", response_model=ConversionRateSchema)
async def get_conversion_rate(
    from_currency: str = Query(..., description="Source currency code (e.g., USD)"),
    to_currency: str = Query(..., description="Target currency code (e.g., EUR)"),
    force_refresh: bool = Query(
        False, description="Force refresh from API instead of using cache"
    ),
    allow_expired: bool = Query(
        False, description="Allow using expired cache entries if API fails"
    ),
    db: AsyncSession = Depends(get_db),
    conversion_service: ConversionService = Depends(get_conversion_service),
) -> Dict[str, Any]:
    """
    Get conversion rate between two currencies with caching.

    Args:
        from_currency: Source currency code (e.g., USD)
        to_currency: Target currency code (e.g., EUR)
        force_refresh: If True, bypass cache and fetch fresh data
        allow_expired: If True, allow using expired cache entries if API fails
        db: Database session
        conversion_service: Conversion service instance

    Returns:
        Dict with conversion rate and cache info
    """
    try:
        result = await conversion_service.get_conversion_rate(
            db=db,
            from_currency=from_currency,
            to_currency=to_currency,
            force_refresh=force_refresh,
            allow_expired=allow_expired,
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get conversion rate: {str(e)}",
        )
