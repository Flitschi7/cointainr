from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

# Corrected imports to include schemas and other modules
from app.crud import crud_asset
from app.models import asset as asset_model
from app.schemas import asset as asset_schema
from app.db.session import SessionLocal

router = APIRouter()


# Dependency to get a DB session
async def get_db():
    async with SessionLocal() as session:
        yield session


@router.post("/", response_model=asset_schema.AssetRead)
async def create_asset(
    *,
    db: AsyncSession = Depends(get_db),
    asset_in: asset_schema.AssetCreate,
) -> asset_model.Asset:
    """
    Create new asset.
    """
    asset = await crud_asset.create_asset(db=db, asset_in=asset_in)
    return asset


@router.get("/", response_model=List[asset_schema.AssetRead])
async def read_assets(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
) -> List[asset_model.Asset]:
    """
    Retrieve assets.
    """
    assets = await crud_asset.get_assets(db=db, skip=skip, limit=limit)
    return assets


@router.delete("/{asset_id}", response_model=asset_schema.AssetRead)
async def delete_asset(
    *,
    db: AsyncSession = Depends(get_db),
    asset_id: int,
) -> asset_model.Asset:
    """
    Delete an asset.
    """
    asset = await crud_asset.delete_asset(db=db, asset_id=asset_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found"
        )
    return asset


@router.put("/{asset_id}", response_model=asset_schema.AssetRead)
async def update_asset(
    *,
    db: AsyncSession = Depends(get_db),
    asset_id: int,
    asset_in: asset_schema.AssetUpdate,
) -> asset_model.Asset:
    """
    Update an asset.
    """
    asset = await crud_asset.get_asset(
        db=db, asset_id=asset_id
    )  # We'll need a get_asset function
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    updated_asset = await crud_asset.update_asset(
        db=db, db_asset=asset, asset_in=asset_in
    )
    return updated_asset
