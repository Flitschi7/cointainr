from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_
from app.models.conversion_cache import ConversionCache
from app.schemas.conversion_cache import ConversionCacheCreate
from datetime import datetime, timedelta
from typing import Optional

# --- Conversion Cache CRUD Operations ---


async def create_conversion_cache(
    db: AsyncSession, *, cache_in: ConversionCacheCreate
) -> ConversionCache:
    """
    Create a new conversion cache entry in the database.
    """
    db_cache = ConversionCache(**cache_in.model_dump())
    db.add(db_cache)
    await db.commit()
    await db.refresh(db_cache)
    return db_cache


async def get_cached_conversion_rate(
    db: AsyncSession, from_currency: str, to_currency: str, max_age_hours: int = 24
) -> Optional[ConversionCache]:
    """
    Get a cached conversion rate for a currency pair if it exists and is not too old.

    Args:
        db: AsyncSession - database session
        from_currency: str - source currency code
        to_currency: str - target currency code
        max_age_hours: int - maximum age of cache entry in hours (default: 24)

    Returns:
        ConversionCache: cached conversion rate if found and fresh, None otherwise
    """
    # If currencies are the same, return rate of 1.0 without caching
    if from_currency.upper() == to_currency.upper():
        return None

    cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)

    result = await db.execute(
        select(ConversionCache)
        .where(
            and_(
                ConversionCache.from_currency == from_currency.upper(),
                ConversionCache.to_currency == to_currency.upper(),
                ConversionCache.fetched_at >= cutoff_time,
            )
        )
        .order_by(ConversionCache.fetched_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def update_or_create_conversion_cache(
    db: AsyncSession,
    from_currency: str,
    to_currency: str,
    rate: float,
    source: str = "exchangerate-api",
) -> ConversionCache:
    """
    Update existing conversion cache entry or create a new one.
    Always creates a new entry with current timestamp.
    """
    cache_data = ConversionCacheCreate(
        from_currency=from_currency.upper(),
        to_currency=to_currency.upper(),
        rate=rate,
        source=source,
    )
    return await create_conversion_cache(db=db, cache_in=cache_data)


async def cleanup_old_conversion_cache_entries(db: AsyncSession, max_age_days: int = 7):
    """
    Remove conversion cache entries older than specified days.

    Args:
        db: AsyncSession - database session
        max_age_days: int - maximum age of cache entries in days (default: 7)
    """
    cutoff_time = datetime.utcnow() - timedelta(days=max_age_days)

    # Use a more efficient batch delete operation
    from sqlalchemy import delete

    # Count entries to be deleted first
    count_query = select(ConversionCache).where(
        ConversionCache.fetched_at < cutoff_time
    )
    result = await db.execute(count_query)
    old_entries = result.scalars().all()
    count = len(old_entries)

    # Execute batch delete
    delete_query = delete(ConversionCache).where(
        ConversionCache.fetched_at < cutoff_time
    )
    await db.execute(delete_query)
    await db.commit()

    return count
