"""
Integration tests for complete cache lifecycle.

Tests the full lifecycle of cache entries including creation, validation, expiration, and invalidation.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock
from sqlalchemy import select
from app.services.cache_management import CacheManagementService, get_utc_now
from app.services.price_service import PriceService
from app.services.conversion_service import ConversionService
from app.models.price_cache import PriceCache
from app.models.conversion_cache import ConversionCache


class TestCacheLifecycleIntegration:
    """Integration tests for complete cache lifecycle."""

    @pytest.fixture
    async def cache_service(self):
        """Create a CacheManagementService instance."""
        return CacheManagementService()

    @pytest.fixture
    async def price_service(self, cache_service):
        """Create a PriceService instance with the cache service."""
        return PriceService(cache_service=cache_service)

    @pytest.fixture
    async def conversion_service(self, cache_service):
        """Create a ConversionService instance with the cache service."""
        return ConversionService(cache_service=cache_service)

    @pytest.mark.asyncio
    async def test_complete_price_cache_lifecycle(
        self, db_session, price_service, cache_service
    ):
        """Test the complete lifecycle of a price cache entry."""
        # 1. Start with a clean state - delete any existing cache for our test symbol
        symbol = "LIFECYCLE_TEST_STOCK"
        query = select(PriceCache).where(PriceCache.symbol == symbol)
        result = await db_session.execute(query)
        for entry in result.scalars().all():
            await db_session.delete(entry)
        await db_session.commit()

        # 2. Mock the external API call to return a controlled price
        with patch.object(
            price_service, "_get_finnhub_stock_price", new_callable=AsyncMock
        ) as mock_get_price:
            mock_get_price.return_value = {
                "symbol": symbol,
                "price": 100.0,
                "currency": "USD",
                "source": "finnhub",
                "timestamp": get_utc_now(),
            }

            # 3. First call should create a new cache entry
            result1 = await price_service.get_stock_price(db_session, symbol)
            assert result1["cached"] is False
            assert result1["price"] == 100.0

            # 4. Second call should use the cache
            result2 = await price_service.get_stock_price(db_session, symbol)
            assert result2["cached"] is True
            assert result2["price"] == 100.0

            # API should have been called only once
            assert mock_get_price.call_count == 1

            # 5. Force refresh should bypass cache
            result3 = await price_service.get_stock_price(
                db_session, symbol, force_refresh=True
            )
            assert result3["cached"] is False
            assert result3["price"] == 100.0

            # API should have been called twice now
            assert mock_get_price.call_count == 2

            # 6. Simulate cache expiration by manipulating the timestamp
            query = select(PriceCache).where(PriceCache.symbol == symbol)
            result = await db_session.execute(query)
            cache_entry = result.scalars().first()

            # Set timestamp to 20 minutes ago (beyond default 15 minute TTL)
            cache_entry.fetched_at = get_utc_now() - timedelta(minutes=20)
            await db_session.commit()

            # 7. Next call should detect expired cache and refresh
            result4 = await price_service.get_stock_price(db_session, symbol)
            assert result4["cached"] is False
            assert result4["price"] == 100.0

            # API should have been called three times now
            assert mock_get_price.call_count == 3

            # 8. Clear the cache explicitly
            clear_result = await cache_service.clear_price_cache(db_session)
            assert clear_result["success"] is True
            assert clear_result["cleared_entries"] >= 1

            # 9. Next call should create a new cache entry
            result5 = await price_service.get_stock_price(db_session, symbol)
            assert result5["cached"] is False
            assert result5["price"] == 100.0

            # API should have been called four times now
            assert mock_get_price.call_count == 4

    @pytest.mark.asyncio
    async def test_currency_conversion_caching(
        self, db_session, conversion_service, cache_service
    ):
        """Test the complete lifecycle of currency conversion cache."""
        # 1. Start with a clean state - delete any existing cache for our test currencies
        from_currency = "USD"
        to_currency = "TEST_EUR"

        query = select(ConversionCache).where(
            (ConversionCache.from_currency == from_currency)
            & (ConversionCache.to_currency == to_currency)
        )
        result = await db_session.execute(query)
        for entry in result.scalars().all():
            await db_session.delete(entry)
        await db_session.commit()

        # 2. Mock the external API call to return a controlled rate
        with patch.object(
            conversion_service, "_fetch_conversion_rate", new_callable=AsyncMock
        ) as mock_fetch_rate:
            mock_fetch_rate.return_value = {
                "from_currency": from_currency,
                "to_currency": to_currency,
                "rate": 0.85,
                "source": "test-api",
                "timestamp": get_utc_now(),
            }

            # 3. First call should create a new cache entry
            result1 = await conversion_service.get_conversion_rate(
                db_session, from_currency, to_currency
            )
            assert result1["cached"] is False
            assert result1["rate"] == 0.85

            # 4. Second call should use the cache
            result2 = await conversion_service.get_conversion_rate(
                db_session, from_currency, to_currency
            )
            assert result2["cached"] is True
            assert result2["rate"] == 0.85

            # API should have been called only once
            assert mock_fetch_rate.call_count == 1

            # 5. Test inverse pair (should use cached rate)
            result3 = await conversion_service.get_conversion_rate(
                db_session, to_currency, from_currency
            )
            assert result3["cached"] is True
            assert (
                abs(result3["rate"] - (1 / 0.85)) < 0.0001
            )  # Should be inverse of 0.85
            assert result3["cache_status"]["is_inverse_pair"] is True

            # API should still have been called only once
            assert mock_fetch_rate.call_count == 1

            # 6. Force refresh should bypass cache
            result4 = await conversion_service.get_conversion_rate(
                db_session, from_currency, to_currency, force_refresh=True
            )
            assert result4["cached"] is False
            assert result4["rate"] == 0.85

            # API should have been called twice now
            assert mock_fetch_rate.call_count == 2

            # 7. Simulate cache expiration by manipulating the timestamp
            query = select(ConversionCache).where(
                (ConversionCache.from_currency == from_currency)
                & (ConversionCache.to_currency == to_currency)
            )
            result = await db_session.execute(query)
            cache_entry = result.scalars().first()

            # Set timestamp to 10 hours ago (beyond default 8 hour TTL)
            cache_entry.fetched_at = get_utc_now() - timedelta(hours=10)
            await db_session.commit()

            # 8. Next call should detect expired cache and refresh
            result5 = await conversion_service.get_conversion_rate(
                db_session, from_currency, to_currency
            )
            assert result5["cached"] is False
            assert result5["rate"] == 0.85

            # API should have been called three times now
            assert mock_fetch_rate.call_count == 3

            # 9. Clear the cache explicitly
            clear_result = await cache_service.clear_conversion_cache(db_session)
            assert clear_result["success"] is True
            assert clear_result["cleared_entries"] >= 1

            # 10. Next call should create a new cache entry
            result6 = await conversion_service.get_conversion_rate(
                db_session, from_currency, to_currency
            )
            assert result6["cached"] is False
            assert result6["rate"] == 0.85

            # API should have been called four times now
            assert mock_fetch_rate.call_count == 4

    @pytest.mark.asyncio
    async def test_cache_invalidation_scenarios(
        self, db_session, price_service, cache_service
    ):
        """Test various cache invalidation scenarios."""
        # 1. Set up test data
        symbol = "INVALIDATION_TEST"

        # Clean up any existing entries
        query = select(PriceCache).where(PriceCache.symbol == symbol)
        result = await db_session.execute(query)
        for entry in result.scalars().all():
            await db_session.delete(entry)
        await db_session.commit()

        # 2. Mock the external API call
        with patch.object(
            price_service, "_get_finnhub_stock_price", new_callable=AsyncMock
        ) as mock_get_price:
            # First call returns one price
            mock_get_price.return_value = {
                "symbol": symbol,
                "price": 100.0,
                "currency": "USD",
                "source": "finnhub",
                "timestamp": get_utc_now(),
            }

            # Create initial cache entry
            result1 = await price_service.get_stock_price(db_session, symbol)
            assert result1["cached"] is False
            assert result1["price"] == 100.0

            # 3. Test scenario: API returns different price on force refresh
            mock_get_price.return_value = {
                "symbol": symbol,
                "price": 110.0,  # Price changed
                "currency": "USD",
                "source": "finnhub",
                "timestamp": get_utc_now(),
            }

            # Force refresh should get new price
            result2 = await price_service.get_stock_price(
                db_session, symbol, force_refresh=True
            )
            assert result2["cached"] is False
            assert result2["price"] == 110.0

            # Normal request should use updated cache
            result3 = await price_service.get_stock_price(db_session, symbol)
            assert result3["cached"] is True
            assert result3["price"] == 110.0

            # 4. Test scenario: Cache entry is deleted from database
            query = select(PriceCache).where(PriceCache.symbol == symbol)
            result = await db_session.execute(query)
            for entry in result.scalars().all():
                await db_session.delete(entry)
            await db_session.commit()

            # Mock a new price
            mock_get_price.return_value = {
                "symbol": symbol,
                "price": 120.0,
                "currency": "USD",
                "source": "finnhub",
                "timestamp": get_utc_now(),
            }

            # Request should create new cache entry
            result4 = await price_service.get_stock_price(db_session, symbol)
            assert result4["cached"] is False
            assert result4["price"] == 120.0

            # 5. Test scenario: API error after cache expiration
            # First, manipulate the timestamp to expire the cache
            query = select(PriceCache).where(PriceCache.symbol == symbol)
            result = await db_session.execute(query)
            cache_entry = result.scalars().first()
            cache_entry.fetched_at = get_utc_now() - timedelta(minutes=20)
            await db_session.commit()

            # Then make the API call fail
            mock_get_price.side_effect = Exception("API Error")

            # Request should try to refresh but fail, and return error
            with pytest.raises(Exception):
                await price_service.get_stock_price(db_session, symbol)

            # 6. Test scenario: Cache statistics after various operations
            stats = await cache_service.get_cache_stats(db_session)

            # Verify structure of stats
            assert "price_cache" in stats
            assert "conversion_cache" in stats
            assert "cache_settings" in stats

            # Price cache should have at least one entry (our test entry)
            assert stats["price_cache"]["count"] >= 1

            # There should be some expired entries
            assert stats["price_cache"]["expired_entries"] >= 1
