from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_
from app.models.price_cache import PriceCache
from app.schemas.price_cache import PriceCacheCreate, PriceCacheUpdate
from datetime import datetime, timedelta
from typing import Optional

# --- Price Cache CRUD Operations ---


async def create_price_cache(
    db: AsyncSession, *, cache_in: PriceCacheCreate
) -> PriceCache:
    """
    Create a new price cache entry in the database.
    """
    db_cache = PriceCache(**cache_in.model_dump())
    db.add(db_cache)
    await db.commit()
    await db.refresh(db_cache)
    return db_cache


async def get_cached_price(
    db: AsyncSession, symbol: str, asset_type: str, max_age_minutes: int = 15
) -> Optional[PriceCache]:
    """
    Get a cached price for a symbol if it exists and is not too old.

    Args:
        db: AsyncSession - database session
        symbol: str - asset symbol/identifier
        asset_type: str - 'stock' or 'crypto'
        max_age_minutes: int - maximum age of cache entry in minutes (default: 15)

    Returns:
        PriceCache: cached price entry if found and fresh, None otherwise
    """
    # Try to use optimized batch query implementation if available
    try:
        from app.services.optimized_cache_queries import get_price_cache_batch

        # Use batch query with a single symbol
        cache_entries = await get_price_cache_batch(
            db, [symbol], asset_type, max_age_minutes
        )
        return cache_entries.get(symbol)

    except ImportError:
        # Fall back to original implementation
        cutoff_time = datetime.utcnow() - timedelta(minutes=max_age_minutes)

        result = await db.execute(
            select(PriceCache)
            .where(
                and_(
                    PriceCache.symbol == symbol,
                    PriceCache.asset_type == asset_type,
                    PriceCache.fetched_at >= cutoff_time,
                )
            )
            .order_by(PriceCache.fetched_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


async def get_cache_by_symbol(
    db: AsyncSession, symbol: str, asset_type: str
) -> Optional[PriceCache]:
    """
    Get the most recent cached price for a symbol regardless of age.

    Args:
        db: AsyncSession - database session
        symbol: str - asset symbol/identifier
        asset_type: str - 'stock' or 'crypto'

    Returns:
        PriceCache: most recent cached price entry if found, None otherwise
    """
    result = await db.execute(
        select(PriceCache)
        .where(
            and_(
                PriceCache.symbol == symbol,
                PriceCache.asset_type == asset_type,
            )
        )
        .order_by(PriceCache.fetched_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def update_or_create_price_cache(
    db: AsyncSession,
    symbol: str,
    asset_type: str,
    price: float,
    currency: str,
    source: str,
) -> PriceCache:
    """
    Update existing price cache entry or create a new one.
    Always creates a new entry with current timestamp.
    """
    cache_data = PriceCacheCreate(
        symbol=symbol,
        asset_type=asset_type,
        price=price,
        currency=currency,
        source=source,
    )
    return await create_price_cache(db=db, cache_in=cache_data)


async def get_cached_prices_batch(
    db: AsyncSession, symbols: list[str], asset_type: str, max_age_minutes: int = 15
) -> dict[str, PriceCache]:
    """
    Get cached prices for multiple symbols in a single query.

    This optimized function fetches multiple cache entries in a single database query,
    reducing the number of round-trips to the database.

    Args:
        db: AsyncSession - database session
        symbols: List[str] - list of asset symbols to fetch
        asset_type: str - 'stock' or 'crypto'
        max_age_minutes: int - maximum age of cache entries in minutes

    Returns:
        Dict mapping symbols to their cache entries
    """
    # Try to use optimized implementation if available
    try:
        from app.services.optimized_cache_queries import get_price_cache_batch

        return await get_price_cache_batch(db, symbols, asset_type, max_age_minutes)
    except ImportError:
        # Fall back to a less optimized but still batched implementation
        cutoff_time = datetime.utcnow() - timedelta(minutes=max_age_minutes)

        # Get all matching cache entries in a single query
        result = await db.execute(
            select(PriceCache)
            .where(
                and_(
                    PriceCache.symbol.in_(symbols),
                    PriceCache.asset_type == asset_type,
                    PriceCache.fetched_at >= cutoff_time,
                )
            )
            .order_by(PriceCache.symbol, PriceCache.fetched_at.desc())
        )

        all_entries = result.scalars().all()

        # Create a dictionary of symbol -> latest cache entry
        cache_dict = {}
        for entry in all_entries:
            if entry.symbol not in cache_dict:
                cache_dict[entry.symbol] = entry

        return cache_dict


async def cleanup_old_cache_entries(db: AsyncSession, max_age_days: int = 30):
    """
    Remove cache entries older than specified days.

    Args:
        db: AsyncSession - database session
        max_age_days: int - maximum age of cache entries in days (default: 30)
    """
    # Try to use optimized implementation if available
    try:
        from app.services.optimized_cache_queries import cleanup_cache_optimized

        result = await cleanup_cache_optimized(db)
        return result.get("price_cache_deleted", 0)
    except ImportError:
        # Fall back to original implementation
        cutoff_time = datetime.utcnow() - timedelta(days=max_age_days)

        # Use a more efficient batch delete operation
        from sqlalchemy import delete

        # Count entries to be deleted first
        count_query = (
            select(func.count())
            .select_from(PriceCache)
            .where(PriceCache.fetched_at < cutoff_time)
        )
        result = await db.execute(count_query)
        count = result.scalar() or 0

        if count > 0:
            # Execute batch delete
            delete_query = delete(PriceCache).where(PriceCache.fetched_at < cutoff_time)
            await db.execute(delete_query)
            await db.commit()

        return count
