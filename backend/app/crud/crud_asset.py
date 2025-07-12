from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.asset import Asset
from app.schemas.asset import AssetCreate


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
