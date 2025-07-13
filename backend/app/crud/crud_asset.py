from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.asset import Asset
from app.schemas.asset import AssetCreate, AssetUpdate

# --- Asset CRUD Operations ---


async def create_asset(db: AsyncSession, *, asset_in: AssetCreate) -> Asset:
    """
    Create a new asset in the database.
    Args:
        db: AsyncSession - database session
        asset_in: AssetCreate - asset data
    Returns:
        Asset: created asset instance
    """
    db_asset = Asset(**asset_in.model_dump())
    db.add(db_asset)
    await db.commit()
    await db.refresh(db_asset)
    return db_asset


async def get_asset(db: AsyncSession, asset_id: int) -> Asset | None:
    """
    Get a single asset by ID.
    Args:
        db: AsyncSession - database session
        asset_id: int - asset ID
    Returns:
        Asset | None: asset instance or None if not found
    """
    result = await db.execute(select(Asset).where(Asset.id == asset_id))
    return result.scalars().first()


async def get_assets(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[Asset]:
    """
    Retrieve all assets from the database with pagination.
    Args:
        db: AsyncSession - database session
        skip: int - number of records to skip
        limit: int - max number of records to return
    Returns:
        list[Asset]: list of asset instances
    """
    result = await db.execute(select(Asset).offset(skip).limit(limit))
    return result.scalars().all()


async def update_asset(
    db: AsyncSession, *, db_asset: Asset, asset_in: AssetUpdate
) -> Asset:
    """
    Update an asset in the database.
    Args:
        db: AsyncSession - database session
        db_asset: Asset - existing asset instance
        asset_in: AssetUpdate - updated asset data
    Returns:
        Asset: updated asset instance
    """
    asset_data = asset_in.model_dump(exclude_unset=True)
    for field, value in asset_data.items():
        setattr(db_asset, field, value)
    db.add(db_asset)
    await db.commit()
    await db.refresh(db_asset)
    return db_asset


async def delete_asset(db: AsyncSession, *, asset_id: int) -> Asset | None:
    """
    Delete an asset from the database by its ID.
    Args:
        db: AsyncSession - database session
        asset_id: int - asset ID
    Returns:
        Asset | None: deleted asset instance or None if not found
    """
    result = await db.execute(select(Asset).where(Asset.id == asset_id))
    asset_to_delete = result.scalars().first()
    if asset_to_delete:
        await db.delete(asset_to_delete)
        await db.commit()
    return asset_to_delete
