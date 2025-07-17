"""
Centralized cache management service for Cointainr.

This service provides consistent cache validation logic across all caching operations,
ensuring that cache TTL settings from .env are respected uniformly.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings


class CacheManagementService:
    """
    Centralized service for managing cache validation and status across the application.

    This service ensures consistent cache behavior by providing unified methods for:
    - Cache validity checking using .env settings
    - Cache expiration calculations
    - Bulk cache status operations
    """

    def __init__(self):
        """Initialize the cache management service with default settings."""
        self._price_cache_minutes = settings.PRICE_CACHE_MINUTES
        self._conversion_cache_hours = settings.CONVERSION_CACHE_HOURS

    def is_price_cache_valid(self, cached_entry: Any) -> bool:
        """
        Check if a price cache entry is still valid based on PRICE_CACHE_MINUTES setting.

        Args:
            cached_entry: Cache entry object with fetched_at timestamp

        Returns:
            bool: True if cache is still valid, False otherwise
        """
        if not cached_entry or not hasattr(cached_entry, "fetched_at"):
            return False

        if not cached_entry.fetched_at:
            return False

        return self._is_cache_valid(cached_entry.fetched_at, self._price_cache_minutes)

    def is_conversion_cache_valid(self, cached_entry: Any) -> bool:
        """
        Check if a conversion cache entry is still valid based on CONVERSION_CACHE_HOURS setting.

        Args:
            cached_entry: Cache entry object with fetched_at timestamp

        Returns:
            bool: True if cache is still valid, False otherwise
        """
        if not cached_entry or not hasattr(cached_entry, "fetched_at"):
            return False

        if not cached_entry.fetched_at:
            return False

        return self._is_cache_valid(
            cached_entry.fetched_at,
            self._conversion_cache_hours * 60,  # Convert hours to minutes
        )

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

        age_delta = datetime.utcnow() - cached_entry.fetched_at
        return int(age_delta.total_seconds() / 60)

    async def get_cache_status_for_assets(
        self, db: AsyncSession, assets: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Get cache status information for multiple assets efficiently.

        Args:
            db: Database session
            assets: List of asset dictionaries with 'id', 'symbol', and 'type' keys

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
                    }

                    # Check if we have a cache entry for this symbol
                    cached_entry = symbol_to_cache.get(symbol)
                    if cached_entry:
                        cache_status["cached_at"] = cached_entry.fetched_at.isoformat()
                        cache_status["is_valid"] = self.is_price_cache_valid(
                            cached_entry
                        )

                        expiration = self.get_price_cache_expiration(cached_entry)
                        if expiration:
                            cache_status["expires_at"] = expiration.isoformat()

                    cache_statuses.append(cache_status)
            except Exception as e:
                logger.error(f"Error processing stock assets: {e}")
                # Fall back to individual processing
                for asset in stock_assets:
                    cache_statuses.append(self._get_single_asset_cache_status(asset))

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
                    }

                    # Check if we have a cache entry for this symbol
                    cached_entry = symbol_to_cache.get(symbol)
                    if cached_entry:
                        cache_status["cached_at"] = cached_entry.fetched_at.isoformat()
                        cache_status["is_valid"] = self.is_price_cache_valid(
                            cached_entry
                        )

                        expiration = self.get_price_cache_expiration(cached_entry)
                        if expiration:
                            cache_status["expires_at"] = expiration.isoformat()

                    cache_statuses.append(cache_status)
            except Exception as e:
                logger.error(f"Error processing crypto assets: {e}")
                # Fall back to individual processing
                for asset in crypto_assets:
                    cache_statuses.append(self._get_single_asset_cache_status(asset))

        # Process other assets individually
        for asset in other_assets:
            cache_statuses.append(self._get_single_asset_cache_status(asset))

        return cache_statuses

    def _get_single_asset_cache_status(self, asset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get cache status for a single asset.

        Args:
            asset: Asset dictionary with 'id', 'symbol', and 'type' keys

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

        age_delta = datetime.utcnow() - fetched_at
        age_minutes = age_delta.total_seconds() / 60

        return age_minutes <= max_age_minutes


# Global instance
cache_management_service = CacheManagementService()
