from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.asset import Asset
from app.schemas.asset import AssetCreate
from app.schemas.asset import AssetUpdate


async def create_asset(db: AsyncSession, *, asset_in: AssetCreate) -> Asset:
    """
    Create a new asset in the database.
    """
    # Create a new SQLAlchemy model instance from the Pydantic schema
    db_asset = Asset(**asset_in.model_dump())

    # Add the instance to the session and commit
    db.add(db_asset)
    await db.commit()
    await db.refresh(db_asset)
    return db_asset


async def get_assets(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[Asset]:
    """
    Retrieve all assets from the database.
    """
    result = await db.execute(select(Asset).offset(skip).limit(limit))
    return result.scalars().all()


# ... (existing functions above)


async def delete_asset(db: AsyncSession, *, asset_id: int) -> Asset | None:
    """
    Delete an asset from the database by its ID.
    """
    result = await db.execute(select(Asset).where(Asset.id == asset_id))
    asset_to_delete = result.scalars().first()
    if asset_to_delete:
        await db.delete(asset_to_delete)
        await db.commit()
    return asset_to_delete


async def update_asset(
    db: AsyncSession, *, db_asset: Asset, asset_in: AssetUpdate
) -> Asset:
    """
    Update an asset in the database.
    """
    asset_data = asset_in.model_dump(exclude_unset=True)
    for field, value in asset_data.items():
        setattr(db_asset, field, value)

    db.add(db_asset)
    await db.commit()
    await db.refresh(db_asset)
    return db_asset


# In backend/app/crud/crud_asset.py


async def get_asset(db: AsyncSession, asset_id: int) -> Asset | None:
    """
    Get a single asset by ID.
    """
    result = await db.execute(select(Asset).where(Asset.id == asset_id))
    return result.scalars().first()
