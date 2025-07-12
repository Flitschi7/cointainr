from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

# Correct, specific imports
from app.crud import crud_asset
from app.models.asset import Asset
from app.schemas.asset import AssetCreate, AssetRead
from app.db.session import SessionLocal

router = APIRouter()


# Dependency to get a DB session
async def get_db():
    async with SessionLocal() as session:
        yield session


# Corrected endpoint definitions using the direct imports
@router.post("/", response_model=AssetRead)
async def create_asset(
    *,
    db: AsyncSession = Depends(get_db),
    asset_in: AssetCreate,
) -> Asset:
    """
    Create new asset.
    """
    asset = await crud_asset.create_asset(db=db, asset_in=asset_in)
    return asset


@router.get("/", response_model=List[AssetRead])
async def read_assets(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
) -> List[Asset]:
    """
    Retrieve assets.
    """
    assets = await crud_asset.get_assets(db=db, skip=skip, limit=limit)
    return assets
