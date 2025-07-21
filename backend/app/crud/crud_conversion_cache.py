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

    # Try to use optimized batch query implementation if available
    try:
        from app.services.optimized_cache_queries import get_conversion_cache_batch

        # Use batch query with a single currency pair
        cache_entries = await get_conversion_cache_batch(
            db, [(from_currency, to_currency)], max_age_hours
        )
        return cache_entries.get((from_currency.upper(), to_currency.upper()))

    except ImportError:
        # Fall back to original implementation
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


async def get_cached_conversion_rates_batch(
    db: AsyncSession, currency_pairs: list[tuple[str, str]], max_age_hours: int = 24
) -> dict[tuple[str, str], ConversionCache]:
    """
    Get cached conversion rates for multiple currency pairs in a single query.

    This optimized function fetches multiple conversion cache entries in a single database query,
    reducing the number of round-trips to the database.

    Args:
        db: AsyncSession - database session
        currency_pairs: List[Tuple[str, str]] - list of (from_currency, to_currency) pairs
        max_age_hours: int - maximum age of cache entries in hours

    Returns:
        Dict mapping currency pairs to their cache entries
    """
    # Filter out pairs where from and to are the same
    valid_pairs = [(f, t) for f, t in currency_pairs if f.upper() != t.upper()]

    if not valid_pairs:
        return {}

    # Try to use optimized implementation if available
    try:
        from app.services.optimized_cache_queries import get_conversion_cache_batch

        return await get_conversion_cache_batch(db, valid_pairs, max_age_hours)
    except ImportError:
        # Fall back to a less optimized but still batched implementation
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)

        # Create OR conditions for each currency pair
        pair_conditions = []
        for from_curr, to_curr in valid_pairs:
            pair_conditions.append(
                and_(
                    ConversionCache.from_currency == from_curr.upper(),
                    ConversionCache.to_currency == to_curr.upper(),
                )
            )

        if not pair_conditions:
            return {}

        # Get all matching cache entries in a single query
        from sqlalchemy import or_

        result = await db.execute(
            select(ConversionCache)
            .where(
                and_(
                    or_(*pair_conditions),
                    ConversionCache.fetched_at >= cutoff_time,
                )
            )
            .order_by(
                ConversionCache.from_currency,
                ConversionCache.to_currency,
                ConversionCache.fetched_at.desc(),
            )
        )

        all_entries = result.scalars().all()

        # Create a dictionary of (from, to) -> latest cache entry
        cache_dict = {}
        for entry in all_entries:
            key = (entry.from_currency, entry.to_currency)
            if key not in cache_dict:
                cache_dict[key] = entry

        return cache_dict


async def cleanup_old_conversion_cache_entries(db: AsyncSession, max_age_days: int = 7):
    """
    Remove conversion cache entries older than specified days.

    Args:
        db: AsyncSession - database session
        max_age_days: int - maximum age of cache entries in days (default: 7)
    """
    # Try to use optimized implementation if available
    try:
        from app.services.optimized_cache_queries import cleanup_cache_optimized

        result = await cleanup_cache_optimized(db)
        return result.get("conversion_cache_deleted", 0)
    except ImportError:
        # Fall back to original implementation
        cutoff_time = datetime.utcnow() - timedelta(days=max_age_days)

        # Use a more efficient batch delete operation
        from sqlalchemy import delete, func

        # Count entries to be deleted first
        count_query = (
            select(func.count())
            .select_from(ConversionCache)
            .where(ConversionCache.fetched_at < cutoff_time)
        )
        result = await db.execute(count_query)
        count = result.scalar() or 0

        if count > 0:
            # Execute batch delete
            delete_query = delete(ConversionCache).where(
                ConversionCache.fetched_at < cutoff_time
            )
            await db.execute(delete_query)
            await db.commit()

        return count
