"""
Unit tests for enhanced PriceService with centralized cache management.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, Mock
from app.services.price_service import PriceService
from app.services.cache_management import CacheManagementService


class TestEnhancedPriceService:
    """Test suite for enhanced PriceService caching behavior."""

    @pytest.fixture
    def price_service(self):
        """Create a PriceService instance with mocked dependencies."""
        cache_service = CacheManagementService()
        return PriceService(cache_service=cache_service)

    @pytest.mark.asyncio
    async def test_get_stock_price_uses_valid_cache(self, price_service):
        """Test that get_stock_price uses valid cached data."""
        # Mock database session
        mock_db = AsyncMock()

        # Mock cached price entry
        mock_cached_price = Mock()
        mock_cached_price.symbol = "AAPL"
        mock_cached_price.price = 150.0
        mock_cached_price.currency = "USD"
        mock_cached_price.source = "finnhub"
        mock_cached_price.fetched_at = datetime.now(timezone.utc) - timedelta(minutes=5)

        with patch(
            "app.crud.crud_price_cache.get_cache_by_symbol"
        ) as mock_get_cache, patch.object(
            CacheManagementService, "is_price_cache_valid"
        ) as mock_is_valid, patch.object(
            CacheManagementService, "get_price_cache_expiration"
        ) as mock_get_expiration:

            mock_get_cache.return_value = mock_cached_price
            mock_is_valid.return_value = True
            mock_get_expiration.return_value = datetime.now(timezone.utc) + timedelta(
                minutes=10
            )

            result = await price_service.get_stock_price(
                mock_db, "AAPL", force_refresh=False
            )

            assert result["symbol"] == "AAPL"
            assert result["price"] == 150.0
            assert result["cached"] is True
            assert "cache_valid_until" in result
            mock_get_cache.assert_called_once_with(
                db=mock_db, symbol="AAPL", asset_type="stock"
            )
            mock_is_valid.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_stock_price_bypasses_cache_on_force_refresh(self, price_service):
        """Test that force_refresh bypasses cache completely."""
        mock_db = AsyncMock()

        with patch(
            "app.crud.crud_price_cache.get_cache_by_symbol"
        ) as mock_get_cache, patch.object(
            price_service, "_get_finnhub_stock_price", new_callable=AsyncMock
        ) as mock_get_finnhub_price, patch(
            "app.crud.crud_price_cache.update_or_create_price_cache",
            new_callable=AsyncMock,
        ) as mock_update_cache:

            # Mock successful API response
            mock_get_finnhub_price.return_value = {
                "symbol": "AAPL",
                "price": 155.0,
                "currency": "USD",
                "source": "finnhub",
                "timestamp": datetime.now(timezone.utc),
            }
            mock_update_cache.return_value = Mock()

            result = await price_service.get_stock_price(
                mock_db, "AAPL", force_refresh=True
            )

            assert result["symbol"] == "AAPL"
            assert result["price"] == 155.0
            assert result["cached"] is False
            assert "cache_valid_until" in result
            # Cache should not be checked when force_refresh=True
            mock_get_cache.assert_not_called()
            mock_get_finnhub_price.assert_called_once_with(mock_db, "AAPL")


if __name__ == "__main__":
    pytest.main([__file__])
