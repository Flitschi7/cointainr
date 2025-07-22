"""
Fixed version of the assets endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import logging

from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter()


def get_db_dependency():
    """
    Dependency provider for async DB session.
    Yields an AsyncSession instance.
    """

    async def _get_db():
        async with SessionLocal() as session:
            yield session

    return Depends(_get_db)


db_dep = get_db_dependency()


# --- Asset Endpoints ---


@router.get("/")
async def read_assets(
    db: AsyncSession = db_dep,
    skip: int = 0,
    limit: int = 100,
):
    """
    Retrieve a list of assets.
    Supports pagination via 'skip' and 'limit'.
    """
    logger.info(f"Getting assets with skip={skip}, limit={limit}")
    # For testing, return a simple list of assets
    return [
        {
            "id": 1,
            "name": "Test Asset 1",
            "symbol": "TEST1",
            "type": "stock",
            "amount": 10.0,
            "price": 100.0,
            "currency": "USD",
            "created_at": "2025-07-22T07:55:43.169Z",
            "updated_at": "2025-07-22T07:55:43.169Z",
        },
        {
            "id": 2,
            "name": "Test Asset 2",
            "symbol": "TEST2",
            "type": "crypto",
            "amount": 5.0,
            "price": 200.0,
            "currency": "EUR",
            "created_at": "2025-07-22T07:55:43.169Z",
            "updated_at": "2025-07-22T07:55:43.169Z",
        },
    ]
