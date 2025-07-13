from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.crud import crud_asset
from app.models import asset as asset_model
from app.schemas import asset as asset_schema
from app.db.session import SessionLocal

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


@router.post("/", response_model=asset_schema.AssetRead)
async def create_asset(
    *,
    db: AsyncSession = db_dep,
    asset_in: asset_schema.AssetCreate,
) -> asset_model.Asset:
    """
    Create a new asset.
    """
    asset = await crud_asset.create_asset(db=db, asset_in=asset_in)
    return asset


@router.get("/", response_model=List[asset_schema.AssetRead])
async def read_assets(
    db: AsyncSession = db_dep,
    skip: int = 0,
    limit: int = 100,
) -> List[asset_model.Asset]:
    """
    Retrieve a list of assets.
    Supports pagination via 'skip' and 'limit'.
    """
    assets = await crud_asset.get_assets(db=db, skip=skip, limit=limit)
    return assets


@router.delete("/{asset_id}", response_model=asset_schema.AssetRead)
async def delete_asset(
    *,
    db: AsyncSession = db_dep,
    asset_id: int,
) -> asset_model.Asset:
    """
    Delete an asset by its ID.
    Returns the deleted asset, or raises 404 if not found.
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
    db: AsyncSession = db_dep,
    asset_id: int,
    asset_in: asset_schema.AssetUpdate,
) -> asset_model.Asset:
    """
    Update an asset by its ID.
    Returns the updated asset, or raises 404 if not found.
    """
    asset = await crud_asset.get_asset(db=db, asset_id=asset_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found"
        )
    updated_asset = await crud_asset.update_asset(
        db=db, db_asset=asset, asset_in=asset_in
    )
    return updated_asset
