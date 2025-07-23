"""
Optimized database queries for cache operations.

This module provides optimized query functions for cache-related operations,
focusing on performance and efficiency for frequently used queries.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, text, case
from sqlalchemy.future import select as future_select
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple

from app.models.price_cache import PriceCache
from app.models.conversion_cache import ConversionCache
from app.core.config import settings


def get_utc_now() -> datetime:
    """
    Get current UTC time with timezone information.

    Returns:
        datetime: Current UTC time with timezone information
    """
    return datetime.now(timezone.utc)


async def get_price_cache_batch(
    db: AsyncSession, symbols: List[str], asset_type: str, max_age_minutes: int
) -> Dict[str, PriceCache]:
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
    if not symbols:
        return {}

    # Calculate cutoff time for cache validity
    cutoff_time = get_utc_now() - timedelta(minutes=max_age_minutes)

    # Use a subquery to get the latest entry for each symbol
    subquery = (
        select(PriceCache.symbol, func.max(PriceCache.fetched_at).label("latest_fetch"))
        .where(
            and_(
                PriceCache.symbol.in_(symbols),
                PriceCache.asset_type == asset_type,
                PriceCache.fetched_at >= cutoff_time,
            )
        )
        .group_by(PriceCache.symbol)
        .subquery()
    )

    # Join with the main table to get the full entries
    query = select(PriceCache).join(
        subquery,
        and_(
            PriceCache.symbol == subquery.c.symbol,
            PriceCache.fetched_at == subquery.c.latest_fetch,
        ),
    )

    # Execute the query
    result = await db.execute(query)
    cache_entries = result.scalars().all()

    # Create a mapping of symbol to cache entry
    return {entry.symbol: entry for entry in cache_entries}


async def get_conversion_cache_batch(
    db: AsyncSession, currency_pairs: List[Tuple[str, str]], max_age_hours: int
) -> Dict[Tuple[str, str], ConversionCache]:
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
    if not currency_pairs:
        return {}

    # Filter out pairs where from and to are the same
    valid_pairs = [
        (f.upper(), t.upper()) for f, t in currency_pairs if f.upper() != t.upper()
    ]

    if not valid_pairs:
        return {}

    # Calculate cutoff time for cache validity
    cutoff_time = get_utc_now() - timedelta(hours=max_age_hours)

    # Create OR conditions for each currency pair
    pair_conditions = []
    for from_curr, to_curr in valid_pairs:
        pair_conditions.append(
            and_(
                ConversionCache.from_currency == from_curr,
                ConversionCache.to_currency == to_curr,
            )
        )

    # Use a subquery to get the latest entry for each currency pair
    subquery = (
        select(
            ConversionCache.from_currency,
            ConversionCache.to_currency,
            func.max(ConversionCache.fetched_at).label("latest_fetch"),
        )
        .where(and_(or_(*pair_conditions), ConversionCache.fetched_at >= cutoff_time))
        .group_by(ConversionCache.from_currency, ConversionCache.to_currency)
        .subquery()
    )

    # Join with the main table to get the full entries
    query = select(ConversionCache).join(
        subquery,
        and_(
            ConversionCache.from_currency == subquery.c.from_currency,
            ConversionCache.to_currency == subquery.c.to_currency,
            ConversionCache.fetched_at == subquery.c.latest_fetch,
        ),
    )

    # Execute the query
    result = await db.execute(query)
    cache_entries = result.scalars().all()

    # Create a mapping of currency pair to cache entry
    return {(entry.from_currency, entry.to_currency): entry for entry in cache_entries}


async def get_cache_statistics_optimized(db: AsyncSession) -> Dict[str, Any]:
    """
    Get comprehensive cache statistics with optimized queries.

    This function uses optimized queries to gather statistics about both price and
    conversion caches, reducing the number of database queries needed.

    Args:
        db: AsyncSession - database session

    Returns:
        Dict with detailed cache statistics
    """
    stats = {
        "price_cache": {
            "total_entries": 0,
            "fresh_entries": 0,
            "stock_entries": 0,
            "crypto_entries": 0,
            "cache_age_minutes": 0,
        },
        "conversion_cache": {
            "total_entries": 0,
            "fresh_entries": 0,
            "cache_age_hours": 0,
        },
    }

    try:
        # Get current time for age calculations
        now = get_utc_now()

        # Calculate cutoff times
        price_cutoff = now - timedelta(minutes=settings.PRICE_CACHE_MINUTES)
        conversion_cutoff = now - timedelta(hours=settings.CONVERSION_CACHE_HOURS)

        # --- Price Cache Statistics (Single Query) ---
        price_stats_query = select(
            func.count().label("total"),
            func.sum(case((PriceCache.fetched_at >= price_cutoff, 1), else_=0)).label(
                "fresh"
            ),
            func.sum(case((PriceCache.asset_type == "stock", 1), else_=0)).label(
                "stock"
            ),
            func.sum(case((PriceCache.asset_type == "crypto", 1), else_=0)).label(
                "crypto"
            ),
            func.min(PriceCache.fetched_at).label("oldest"),
            func.max(PriceCache.fetched_at).label("newest"),
        ).select_from(PriceCache)

        # Execute price stats query
        price_result = await db.execute(price_stats_query)
        price_row = price_result.fetchone()

        if price_row and price_row.total > 0:
            stats["price_cache"]["total_entries"] = price_row.total
            stats["price_cache"]["fresh_entries"] = price_row.fresh or 0
            stats["price_cache"]["stock_entries"] = price_row.stock or 0
            stats["price_cache"]["crypto_entries"] = price_row.crypto or 0

            # Calculate average age if we have both oldest and newest
            if price_row.oldest and price_row.newest:
                oldest_age = (now - price_row.oldest).total_seconds() / 60
                newest_age = (now - price_row.newest).total_seconds() / 60
                stats["price_cache"]["cache_age_minutes"] = int(
                    (oldest_age + newest_age) / 2
                )

        # --- Conversion Cache Statistics (Single Query) ---
        conversion_stats_query = select(
            func.count().label("total"),
            func.sum(
                case((ConversionCache.fetched_at >= conversion_cutoff, 1), else_=0)
            ).label("fresh"),
            func.min(ConversionCache.fetched_at).label("oldest"),
            func.max(ConversionCache.fetched_at).label("newest"),
        ).select_from(ConversionCache)

        # Execute conversion stats query
        conversion_result = await db.execute(conversion_stats_query)
        conversion_row = conversion_result.fetchone()

        if conversion_row and conversion_row.total > 0:
            stats["conversion_cache"]["total_entries"] = conversion_row.total
            stats["conversion_cache"]["fresh_entries"] = conversion_row.fresh or 0

            # Calculate average age if we have both oldest and newest
            if conversion_row.oldest and conversion_row.newest:
                oldest_age = (now - conversion_row.oldest).total_seconds() / 3600
                newest_age = (now - conversion_row.newest).total_seconds() / 3600
                stats["conversion_cache"]["cache_age_hours"] = round(
                    (oldest_age + newest_age) / 2, 1
                )

    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error getting optimized cache statistics: {e}")

    return stats


async def cleanup_cache_optimized(db: AsyncSession) -> Dict[str, int]:
    """
    Clean up old cache entries with optimized batch operations.

    This function uses optimized batch delete operations to remove old cache entries,
    improving performance for cleanup tasks.

    Args:
        db: AsyncSession - database session

    Returns:
        Dict with counts of deleted entries
    """
    result = {"price_cache_deleted": 0, "conversion_cache_deleted": 0}

    try:
        # Calculate cutoff times
        price_cutoff = get_utc_now() - timedelta(days=settings.PRICE_CACHE_CLEANUP_DAYS)
        conversion_cutoff = get_utc_now() - timedelta(
            days=settings.CONVERSION_CACHE_CLEANUP_DAYS
        )

        # Use efficient count queries
        price_count_query = (
            select(func.count())
            .select_from(PriceCache)
            .where(PriceCache.fetched_at < price_cutoff)
        )
        price_count_result = await db.execute(price_count_query)
        price_count = price_count_result.scalar() or 0

        conversion_count_query = (
            select(func.count())
            .select_from(ConversionCache)
            .where(ConversionCache.fetched_at < conversion_cutoff)
        )
        conversion_count_result = await db.execute(conversion_count_query)
        conversion_count = conversion_count_result.scalar() or 0

        # Only proceed with deletion if there are entries to delete
        if price_count > 0:
            # Use efficient batch delete
            from sqlalchemy import delete

            price_delete = delete(PriceCache).where(
                PriceCache.fetched_at < price_cutoff
            )
            await db.execute(price_delete)
            result["price_cache_deleted"] = price_count

        if conversion_count > 0:
            # Use efficient batch delete
            from sqlalchemy import delete

            conversion_delete = delete(ConversionCache).where(
                ConversionCache.fetched_at < conversion_cutoff
            )
            await db.execute(conversion_delete)
            result["conversion_cache_deleted"] = conversion_count

        # Commit the transaction if any deletions were performed
        if price_count > 0 or conversion_count > 0:
            await db.commit()

            # For SQLite, run VACUUM to reclaim space
            if settings.DATABASE_URL.startswith("sqlite"):
                await db.execute(text("VACUUM"))
                await db.commit()

    except Exception as e:
        await db.rollback()
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error during optimized cache cleanup: {e}")

    return result
