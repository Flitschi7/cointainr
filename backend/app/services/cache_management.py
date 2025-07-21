"""
Centralized cache management service for Cointainr.

This service provides consistent cache validation logic across all caching operations,
ensuring that cache TTL settings from .env are respected uniformly.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Tuple
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, delete
from sqlalchemy.exc import SQLAlchemyError
from app.core.config import settings
from app.models.price_cache import PriceCache
from app.models.conversion_cache import ConversionCache

# Set up logger
logger = logging.getLogger(__name__)


def get_utc_now() -> datetime:
    """
    Get current UTC time with timezone information.

    Returns:
        datetime: Current UTC time with timezone information
    """
    return datetime.now(timezone.utc)


def ensure_timezone_aware(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Ensure a datetime object has timezone information.
    If the datetime is naive (no timezone), assume it's UTC and add timezone info.

    Args:
        dt: Datetime object to check

    Returns:
        datetime: Timezone-aware datetime object, or None if input was None
    """
    if dt is None:
        return None

    if dt.tzinfo is None:
        # If datetime has no timezone info, assume it's UTC
        return dt.replace(tzinfo=timezone.utc)

    return dt


class CacheManagementService:
    """
    Centralized service for managing cache validation and status across the application.

    This service ensures consistent cache behavior by providing unified methods for:
    - Cache validity checking using .env settings
    - Cache expiration calculations
    - Bulk cache status operations
    - Cache statistics tracking and reporting
    """

    def __init__(self):
        """Initialize the cache management service with default settings."""
        self._price_cache_minutes = settings.PRICE_CACHE_MINUTES
        self._conversion_cache_hours = settings.CONVERSION_CACHE_HOURS

        # Cache hit/miss tracking
        self._price_cache_hits = 0
        self._price_cache_misses = 0
        self._conversion_cache_hits = 0
        self._conversion_cache_misses = 0

    def is_price_cache_valid(
        self, cached_entry: Any, force_refresh: bool = False
    ) -> bool:
        """
        Check if a price cache entry is still valid based on PRICE_CACHE_MINUTES setting.

        Args:
            cached_entry: Cache entry object with fetched_at timestamp
            force_refresh: If True, always return False to force a refresh

        Returns:
            bool: True if cache is still valid, False otherwise
        """
        # If force refresh is requested, always return False
        if force_refresh:
            return False

        if not cached_entry or not hasattr(cached_entry, "fetched_at"):
            self._price_cache_misses += 1
            # Track in performance monitoring
            try:
                from app.core.performance_monitoring import record_cache_access

                record_cache_access("price", False)
            except ImportError:
                pass
            return False

        if not cached_entry.fetched_at:
            self._price_cache_misses += 1
            # Track in performance monitoring
            try:
                from app.core.performance_monitoring import record_cache_access

                record_cache_access("price", False)
            except ImportError:
                pass
            return False

        # Use environment variable for TTL calculation
        is_valid = self._is_cache_valid(
            cached_entry.fetched_at, self._price_cache_minutes
        )

        # Track cache hit/miss
        if is_valid:
            self._price_cache_hits += 1
            # Track in performance monitoring
            try:
                from app.core.performance_monitoring import record_cache_access

                record_cache_access("price", True)
            except ImportError:
                pass
        else:
            self._price_cache_misses += 1
            # Track in performance monitoring
            try:
                from app.core.performance_monitoring import record_cache_access

                record_cache_access("price", False)
            except ImportError:
                pass

        return is_valid

    def is_conversion_cache_valid(
        self, cached_entry: Any, force_refresh: bool = False
    ) -> bool:
        """
        Check if a conversion cache entry is still valid based on CONVERSION_CACHE_HOURS setting.

        Args:
            cached_entry: Cache entry object with fetched_at timestamp
            force_refresh: If True, always return False to force a refresh

        Returns:
            bool: True if cache is still valid, False otherwise
        """
        # If force refresh is requested, always return False
        if force_refresh:
            return False

        if not cached_entry or not hasattr(cached_entry, "fetched_at"):
            self._conversion_cache_misses += 1
            # Track in performance monitoring
            try:
                from app.core.performance_monitoring import record_cache_access

                record_cache_access("conversion", False)
            except ImportError:
                pass
            return False

        if not cached_entry.fetched_at:
            self._conversion_cache_misses += 1
            # Track in performance monitoring
            try:
                from app.core.performance_monitoring import record_cache_access

                record_cache_access("conversion", False)
            except ImportError:
                pass
            return False

        # Use environment variable for TTL calculation
        is_valid = self._is_cache_valid(
            cached_entry.fetched_at,
            self._conversion_cache_hours * 60,  # Convert hours to minutes
        )

        # Track cache hit/miss
        if is_valid:
            self._conversion_cache_hits += 1
            # Track in performance monitoring
            try:
                from app.core.performance_monitoring import record_cache_access

                record_cache_access("conversion", True)
            except ImportError:
                pass
        else:
            self._conversion_cache_misses += 1
            # Track in performance monitoring
            try:
                from app.core.performance_monitoring import record_cache_access

                record_cache_access("conversion", False)
            except ImportError:
                pass

        return is_valid

    def get_price_cache_expiration(self, cached_entry: Any) -> Optional[datetime]:
        """
        Calculate when a price cache entry will expire.

        Args:
            cached_entry: Cache entry object with fetched_at timestamp

        Returns:
            datetime: When the cache expires, or None if entry is invalid
        """
        if not cached_entry or not hasattr(cached_entry, "fetched_at"):
            return None

        if not cached_entry.fetched_at:
            return None

        return cached_entry.fetched_at + timedelta(minutes=self._price_cache_minutes)

    def get_conversion_cache_expiration(self, cached_entry: Any) -> Optional[datetime]:
        """
        Calculate when a conversion cache entry will expire.

        Args:
            cached_entry: Cache entry object with fetched_at timestamp

        Returns:
            datetime: When the cache expires, or None if entry is invalid
        """
        if not cached_entry or not hasattr(cached_entry, "fetched_at"):
            return None

        if not cached_entry.fetched_at:
            return None

        return cached_entry.fetched_at + timedelta(hours=self._conversion_cache_hours)

    def get_cache_age_minutes(self, cached_entry: Any) -> Optional[int]:
        """
        Calculate how many minutes old a cache entry is.

        Args:
            cached_entry: Cache entry object with fetched_at timestamp

        Returns:
            int: Age in minutes, or None if entry is invalid
        """
        if not cached_entry or not hasattr(cached_entry, "fetched_at"):
            return None

        if not cached_entry.fetched_at:
            return None

        # Ensure fetched_at is timezone-aware
        fetched_at = ensure_timezone_aware(cached_entry.fetched_at)

        # Get current time with timezone information
        now = get_utc_now()

        # Calculate age using timezone-aware objects
        age_delta = now - fetched_at

        return int(age_delta.total_seconds() / 60)

    def get_cache_status(
        self, cached_entry: Any, ttl_minutes: int, force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Get detailed cache status information for a single cache entry.

        Args:
            cached_entry: Cache entry object with fetched_at timestamp
            ttl_minutes: TTL in minutes for this cache type
            force_refresh: If True, cache will be considered invalid

        Returns:
            Dict with cache status information
        """
        status = {
            "is_valid": False,
            "cached_at": None,
            "expires_at": None,
            "cache_age_minutes": None,
            "ttl_minutes": ttl_minutes,
            "force_refresh_requested": force_refresh,
        }

        if (
            not cached_entry
            or not hasattr(cached_entry, "fetched_at")
            or not cached_entry.fetched_at
        ):
            return status

        # Calculate cache status
        status["is_valid"] = not force_refresh and self._is_cache_valid(
            cached_entry.fetched_at, ttl_minutes
        )
        status["cached_at"] = cached_entry.fetched_at.isoformat()

        # Calculate expiration
        expiration = cached_entry.fetched_at + timedelta(minutes=ttl_minutes)
        status["expires_at"] = expiration.isoformat()

        # Ensure fetched_at is timezone-aware and calculate age
        fetched_at = ensure_timezone_aware(cached_entry.fetched_at)
        now = get_utc_now()
        age_delta = now - fetched_at
        status["cache_age_minutes"] = int(age_delta.total_seconds() / 60)

        return status

    async def get_cache_status_for_assets(
        self,
        db: AsyncSession,
        assets: List[Dict[str, Any]],
        force_refresh: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get cache status information for multiple assets efficiently.

        Args:
            db: Database session
            assets: List of asset dictionaries with 'id', 'symbol', and 'type' keys
            force_refresh: If True, all cache entries will be considered invalid

        Returns:
            List of cache status dictionaries with validity information
        """
        # Import here to avoid circular dependency
        from app.crud import crud_price_cache
        from sqlalchemy import select, and_
        from app.models.price_cache import PriceCache
        import logging

        logger = logging.getLogger(__name__)
        cache_statuses = []

        # Group assets by type for batch processing
        stock_assets = []
        crypto_assets = []
        other_assets = []

        for asset in assets:
            asset_id = asset.get("id")
            symbol = asset.get("symbol")
            asset_type = asset.get("type")

            if not all([asset_id, symbol, asset_type]):
                continue

            if asset_type.lower() == "stock":
                stock_assets.append(asset)
            elif asset_type.lower() == "crypto":
                crypto_assets.append(asset)
            else:
                other_assets.append(asset)

        # Process stock assets in batch
        if stock_assets:
            try:
                # Get all stock symbols
                stock_symbols = [asset.get("symbol") for asset in stock_assets]

                # Fetch all cache entries for these symbols in a single query
                query = (
                    select(PriceCache)
                    .where(
                        and_(
                            PriceCache.symbol.in_(stock_symbols),
                            PriceCache.asset_type == "stock",
                        )
                    )
                    .order_by(PriceCache.fetched_at.desc())
                )

                result = await db.execute(query)
                cached_entries = result.scalars().all()

                # Create a map of symbol to latest cache entry
                symbol_to_cache = {}
                for entry in cached_entries:
                    if entry.symbol not in symbol_to_cache:
                        symbol_to_cache[entry.symbol] = entry

                # Process each stock asset
                for asset in stock_assets:
                    asset_id = asset.get("id")
                    symbol = asset.get("symbol")

                    cache_status = {
                        "asset_id": asset_id,
                        "symbol": symbol,
                        "type": "stock",
                        "cached_at": None,
                        "cache_ttl_minutes": self._price_cache_minutes,
                        "is_valid": False,
                        "expires_at": None,
                        "force_refresh_requested": force_refresh,
                    }

                    # Check if we have a cache entry for this symbol
                    cached_entry = symbol_to_cache.get(symbol)
                    if cached_entry:
                        cache_status["cached_at"] = cached_entry.fetched_at.isoformat()
                        cache_status["is_valid"] = self.is_price_cache_valid(
                            cached_entry, force_refresh
                        )

                        # Add cache age information for better reporting
                        cache_age = self.get_cache_age_minutes(cached_entry)
                        if cache_age is not None:
                            cache_status["cache_age_minutes"] = cache_age

                        expiration = self.get_price_cache_expiration(cached_entry)
                        if expiration:
                            cache_status["expires_at"] = expiration.isoformat()

                    cache_statuses.append(cache_status)
            except Exception as e:
                logger.error(f"Error processing stock assets: {e}")
                # Fall back to individual processing
                for asset in stock_assets:
                    cache_statuses.append(
                        self._get_single_asset_cache_status(asset, force_refresh)
                    )

        # Process crypto assets in batch (similar to stocks)
        if crypto_assets:
            try:
                # Get all crypto symbols
                crypto_symbols = [asset.get("symbol") for asset in crypto_assets]

                # Fetch all cache entries for these symbols in a single query
                query = (
                    select(PriceCache)
                    .where(
                        and_(
                            PriceCache.symbol.in_(crypto_symbols),
                            PriceCache.asset_type == "crypto",
                        )
                    )
                    .order_by(PriceCache.fetched_at.desc())
                )

                result = await db.execute(query)
                cached_entries = result.scalars().all()

                # Create a map of symbol to latest cache entry
                symbol_to_cache = {}
                for entry in cached_entries:
                    if entry.symbol not in symbol_to_cache:
                        symbol_to_cache[entry.symbol] = entry

                # Process each crypto asset
                for asset in crypto_assets:
                    asset_id = asset.get("id")
                    symbol = asset.get("symbol")

                    cache_status = {
                        "asset_id": asset_id,
                        "symbol": symbol,
                        "type": "crypto",
                        "cached_at": None,
                        "cache_ttl_minutes": self._price_cache_minutes,
                        "is_valid": False,
                        "expires_at": None,
                        "force_refresh_requested": force_refresh,
                    }

                    # Check if we have a cache entry for this symbol
                    cached_entry = symbol_to_cache.get(symbol)
                    if cached_entry:
                        cache_status["cached_at"] = cached_entry.fetched_at.isoformat()
                        cache_status["is_valid"] = self.is_price_cache_valid(
                            cached_entry, force_refresh
                        )

                        # Add cache age information for better reporting
                        cache_age = self.get_cache_age_minutes(cached_entry)
                        if cache_age is not None:
                            cache_status["cache_age_minutes"] = cache_age

                        expiration = self.get_price_cache_expiration(cached_entry)
                        if expiration:
                            cache_status["expires_at"] = expiration.isoformat()

                    cache_statuses.append(cache_status)
            except Exception as e:
                logger.error(f"Error processing crypto assets: {e}")
                # Fall back to individual processing
                for asset in crypto_assets:
                    cache_statuses.append(
                        self._get_single_asset_cache_status(asset, force_refresh)
                    )

        # Process other assets individually
        for asset in other_assets:
            cache_statuses.append(
                self._get_single_asset_cache_status(asset, force_refresh)
            )

        return cache_statuses

    def _get_single_asset_cache_status(
        self, asset: Dict[str, Any], force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Get cache status for a single asset.

        Args:
            asset: Asset dictionary with 'id', 'symbol', and 'type' keys
            force_refresh: If True, cache will be considered invalid

        Returns:
            Cache status dictionary
        """
        asset_id = asset.get("id")
        symbol = asset.get("symbol")
        asset_type = asset.get("type")

        return {
            "asset_id": asset_id,
            "symbol": symbol,
            "type": asset_type,
            "cached_at": None,
            "cache_ttl_minutes": (
                self._price_cache_minutes
                if asset_type.lower() in ["stock", "crypto"]
                else None
            ),
            "is_valid": False,
            "expires_at": None,
            "force_refresh_requested": force_refresh,
        }

    def get_cache_settings(self) -> Dict[str, int]:
        """
        Get current cache settings from configuration.

        Returns:
            Dict with current cache TTL settings
        """
        return {
            "price_cache_minutes": self._price_cache_minutes,
            "conversion_cache_hours": self._conversion_cache_hours,
            "price_cache_cleanup_days": settings.PRICE_CACHE_CLEANUP_DAYS,
            "conversion_cache_cleanup_days": settings.CONVERSION_CACHE_CLEANUP_DAYS,
        }

    async def get_cache_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Get comprehensive statistics about both price and conversion caches.

        This method provides detailed information about:
        - Cache entry counts
        - Cache hit/miss rates
        - Cache age statistics (min, max, average)
        - Cache distribution by age

        Args:
            db: AsyncSession - database session

        Returns:
            Dict with detailed cache statistics
        """
        try:
            # Use optimized query implementation if available
            try:
                from app.services.optimized_cache_queries import (
                    get_cache_statistics_optimized,
                )

                # Get optimized cache statistics (fewer queries)
                stats = await get_cache_statistics_optimized(db)

                # Add hit/miss statistics from this instance
                stats["price_cache"]["hit_count"] = self._price_cache_hits
                stats["price_cache"]["miss_count"] = self._price_cache_misses
                stats["conversion_cache"]["hit_count"] = self._conversion_cache_hits
                stats["conversion_cache"]["miss_count"] = self._conversion_cache_misses

                # Calculate hit rates
                price_total = (
                    stats["price_cache"]["hit_count"]
                    + stats["price_cache"]["miss_count"]
                )
                if price_total > 0:
                    stats["price_cache"]["hit_rate"] = round(
                        stats["price_cache"]["hit_count"] / price_total * 100, 2
                    )
                else:
                    stats["price_cache"]["hit_rate"] = 0.0

                conv_total = (
                    stats["conversion_cache"]["hit_count"]
                    + stats["conversion_cache"]["miss_count"]
                )
                if conv_total > 0:
                    stats["conversion_cache"]["hit_rate"] = round(
                        stats["conversion_cache"]["hit_count"] / conv_total * 100, 2
                    )
                else:
                    stats["conversion_cache"]["hit_rate"] = 0.0

                # Add cache settings
                stats["cache_settings"] = self.get_cache_settings()

                return stats

            except ImportError:
                # Fall back to original implementation if optimized queries are not available
                # Get price cache statistics
                price_cache_stats = await self._get_price_cache_stats(db)

                # Get conversion cache statistics
                conversion_cache_stats = await self._get_conversion_cache_stats(db)

                # Combine statistics
                return {
                    "price_cache": price_cache_stats,
                    "conversion_cache": conversion_cache_stats,
                    "cache_settings": self.get_cache_settings(),
                }

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error getting cache statistics: {e}")

            # Return default stats on error
            return {
                "price_cache": {
                    "count": 0,
                    "hit_count": self._price_cache_hits,
                    "miss_count": self._price_cache_misses,
                    "hit_rate": 0.0,
                    "error": str(e),
                },
                "conversion_cache": {
                    "count": 0,
                    "hit_count": self._conversion_cache_hits,
                    "miss_count": self._conversion_cache_misses,
                    "hit_rate": 0.0,
                    "error": str(e),
                },
                "cache_settings": self.get_cache_settings(),
            }

    async def _get_price_cache_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Get detailed statistics about the price cache.

        Args:
            db: AsyncSession - database session

        Returns:
            Dict with price cache statistics
        """
        stats = {
            "count": 0,
            "hit_count": self._price_cache_hits,
            "miss_count": self._price_cache_misses,
            "hit_rate": 0.0,
            "average_age_minutes": 0,
            "oldest_entry_minutes": 0,
            "newest_entry_minutes": 0,
            "valid_entries": 0,
            "expired_entries": 0,
            "by_asset_type": {},
            "by_source": {},
        }

        # Calculate hit rate if there have been any cache accesses
        total_accesses = stats["hit_count"] + stats["miss_count"]
        if total_accesses > 0:
            stats["hit_rate"] = round(stats["hit_count"] / total_accesses * 100, 2)

        try:
            # Get total count of cache entries
            count_query = select(func.count()).select_from(PriceCache)
            result = await db.execute(count_query)
            stats["count"] = result.scalar() or 0

            if stats["count"] == 0:
                return stats

            # Get average age in minutes
            now = get_utc_now()

            # Get oldest entry
            oldest_query = (
                select(PriceCache).order_by(PriceCache.fetched_at.asc()).limit(1)
            )
            result = await db.execute(oldest_query)
            oldest_entry = result.scalar_one_or_none()
            if oldest_entry:
                # Ensure fetched_at is timezone-aware
                fetched_at = ensure_timezone_aware(oldest_entry.fetched_at)
                age_delta = now - fetched_at
                stats["oldest_entry_minutes"] = int(age_delta.total_seconds() / 60)

            # Get newest entry
            newest_query = (
                select(PriceCache).order_by(PriceCache.fetched_at.desc()).limit(1)
            )
            result = await db.execute(newest_query)
            newest_entry = result.scalar_one_or_none()
            if newest_entry:
                # Ensure fetched_at is timezone-aware
                fetched_at = ensure_timezone_aware(newest_entry.fetched_at)
                age_delta = now - fetched_at
                stats["newest_entry_minutes"] = int(age_delta.total_seconds() / 60)

            # Count valid vs expired entries
            cutoff_time = get_utc_now() - timedelta(minutes=self._price_cache_minutes)
            valid_query = (
                select(func.count())
                .select_from(PriceCache)
                .where(PriceCache.fetched_at >= cutoff_time)
            )
            result = await db.execute(valid_query)
            stats["valid_entries"] = result.scalar() or 0
            stats["expired_entries"] = stats["count"] - stats["valid_entries"]

            # Get distribution by asset type
            asset_type_query = (
                select(PriceCache.asset_type, func.count())
                .select_from(PriceCache)
                .group_by(PriceCache.asset_type)
            )
            result = await db.execute(asset_type_query)
            for asset_type, count in result.all():
                stats["by_asset_type"][asset_type] = count

            # Get distribution by source
            source_query = (
                select(PriceCache.source, func.count())
                .select_from(PriceCache)
                .group_by(PriceCache.source)
            )
            result = await db.execute(source_query)
            for source, count in result.all():
                stats["by_source"][source] = count

            # Calculate average age if there are entries
            if stats["count"] > 0:
                # This is an approximation based on oldest and newest entries
                stats["average_age_minutes"] = int(
                    (stats["oldest_entry_minutes"] + stats["newest_entry_minutes"]) / 2
                )

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error getting price cache statistics: {e}")

        return stats

    async def _get_conversion_cache_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Get detailed statistics about the conversion cache.

        Args:
            db: AsyncSession - database session

        Returns:
            Dict with conversion cache statistics
        """
        stats = {
            "count": 0,
            "hit_count": self._conversion_cache_hits,
            "miss_count": self._conversion_cache_misses,
            "hit_rate": 0.0,
            "average_age_hours": 0,
            "oldest_entry_hours": 0,
            "newest_entry_hours": 0,
            "valid_entries": 0,
            "expired_entries": 0,
            "currency_pairs": 0,
            "by_source": {},
        }

        # Calculate hit rate if there have been any cache accesses
        total_accesses = stats["hit_count"] + stats["miss_count"]
        if total_accesses > 0:
            stats["hit_rate"] = round(stats["hit_count"] / total_accesses * 100, 2)

        try:
            # Get total count of cache entries
            count_query = select(func.count()).select_from(ConversionCache)
            result = await db.execute(count_query)
            stats["count"] = result.scalar() or 0

            if stats["count"] == 0:
                return stats

            # Get average age in hours
            now = get_utc_now()

            # Get oldest entry
            oldest_query = (
                select(ConversionCache)
                .order_by(ConversionCache.fetched_at.asc())
                .limit(1)
            )
            result = await db.execute(oldest_query)
            oldest_entry = result.scalar_one_or_none()
            if oldest_entry:
                # Ensure fetched_at is timezone-aware
                fetched_at = ensure_timezone_aware(oldest_entry.fetched_at)
                age_delta = now - fetched_at
                stats["oldest_entry_hours"] = round(age_delta.total_seconds() / 3600, 1)

            # Get newest entry
            newest_query = (
                select(ConversionCache)
                .order_by(ConversionCache.fetched_at.desc())
                .limit(1)
            )
            result = await db.execute(newest_query)
            newest_entry = result.scalar_one_or_none()
            if newest_entry:
                # Ensure fetched_at is timezone-aware
                fetched_at = ensure_timezone_aware(newest_entry.fetched_at)
                age_delta = now - fetched_at
                stats["newest_entry_hours"] = round(age_delta.total_seconds() / 3600, 1)

            # Count valid vs expired entries
            cutoff_time = get_utc_now() - timedelta(hours=self._conversion_cache_hours)
            valid_query = (
                select(func.count())
                .select_from(ConversionCache)
                .where(ConversionCache.fetched_at >= cutoff_time)
            )
            result = await db.execute(valid_query)
            stats["valid_entries"] = result.scalar() or 0
            stats["expired_entries"] = stats["count"] - stats["valid_entries"]

            # Count unique currency pairs
            pairs_query = select(
                func.count(
                    func.distinct(
                        ConversionCache.from_currency, ConversionCache.to_currency
                    )
                )
            ).select_from(ConversionCache)
            result = await db.execute(pairs_query)
            stats["currency_pairs"] = result.scalar() or 0

            # Get distribution by source
            source_query = (
                select(ConversionCache.source, func.count())
                .select_from(ConversionCache)
                .group_by(ConversionCache.source)
            )
            result = await db.execute(source_query)
            for source, count in result.all():
                stats["by_source"][source] = count

            # Calculate average age if there are entries
            if stats["count"] > 0:
                # This is an approximation based on oldest and newest entries
                stats["average_age_hours"] = round(
                    (stats["oldest_entry_hours"] + stats["newest_entry_hours"]) / 2, 1
                )

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error getting conversion cache statistics: {e}")

        return stats

    async def clear_price_cache(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Clear all price cache entries from the database.

        This method removes all entries from the price_cache table using a transaction
        to ensure data consistency.

        Args:
            db: AsyncSession - database session

        Returns:
            Dict with operation status and count of cleared entries
        """
        result = {"success": False, "cleared_entries": 0, "error": None}

        try:
            # Get count of entries before deletion for reporting
            count_query = select(func.count()).select_from(PriceCache)
            count_result = await db.execute(count_query)
            entry_count = count_result.scalar() or 0

            if entry_count == 0:
                # No entries to delete
                result["success"] = True
                return result

            # Create delete statement
            delete_stmt = delete(PriceCache)

            # Execute within transaction
            await db.execute(delete_stmt)
            await db.commit()

            # Update result
            result["success"] = True
            result["cleared_entries"] = entry_count

            # Log the operation
            logger.info(f"Successfully cleared {entry_count} price cache entries")

        except SQLAlchemyError as e:
            # Roll back transaction on error
            await db.rollback()
            error_msg = f"Database error while clearing price cache: {str(e)}"
            logger.error(error_msg)
            result["error"] = error_msg

        except Exception as e:
            # Roll back transaction on any other error
            await db.rollback()
            error_msg = f"Unexpected error while clearing price cache: {str(e)}"
            logger.error(error_msg)
            result["error"] = error_msg

        return result

    async def clear_conversion_cache(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Clear all currency conversion cache entries from the database.

        This method removes all entries from the conversion_cache table using a transaction
        to ensure data consistency.

        Args:
            db: AsyncSession - database session

        Returns:
            Dict with operation status and count of cleared entries
        """
        result = {"success": False, "cleared_entries": 0, "error": None}

        try:
            # Get count of entries before deletion for reporting
            count_query = select(func.count()).select_from(ConversionCache)
            count_result = await db.execute(count_query)
            entry_count = count_result.scalar() or 0

            if entry_count == 0:
                # No entries to delete
                result["success"] = True
                return result

            # Create delete statement
            delete_stmt = delete(ConversionCache)

            # Execute within transaction
            await db.execute(delete_stmt)
            await db.commit()

            # Update result
            result["success"] = True
            result["cleared_entries"] = entry_count

            # Log the operation
            logger.info(f"Successfully cleared {entry_count} conversion cache entries")

        except SQLAlchemyError as e:
            # Roll back transaction on error
            await db.rollback()
            error_msg = f"Database error while clearing conversion cache: {str(e)}"
            logger.error(error_msg)
            result["error"] = error_msg

        except Exception as e:
            # Roll back transaction on any other error
            await db.rollback()
            error_msg = f"Unexpected error while clearing conversion cache: {str(e)}"
            logger.error(error_msg)
            result["error"] = error_msg

        return result

    def _is_cache_valid(self, fetched_at: datetime, max_age_minutes: int) -> bool:
        """
        Internal helper method to check if cache is valid based on age.

        Args:
            fetched_at: When the cache entry was created
            max_age_minutes: Maximum age in minutes before cache is considered stale

        Returns:
            bool: True if cache is still valid
        """
        if not fetched_at:
            return False

        # Ensure fetched_at is timezone-aware
        fetched_at = ensure_timezone_aware(fetched_at)

        # Get current time with timezone information
        now = get_utc_now()

        # Calculate age using timezone-aware objects
        age_delta = now - fetched_at

        age_minutes = age_delta.total_seconds() / 60

        return age_minutes <= max_age_minutes


# Global instance
cache_management_service = CacheManagementService()
