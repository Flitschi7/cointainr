"""
Unit tests for enhanced PriceService with centralized cache management.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, Mock
from app.services.price_service import price_service
from app.services.cache_management import cache_management_service


class TestEnhancedPriceService:
    """Test suite for enhanced PriceService caching behavior."""

    @pytest.mark.asyncio
    async def test_get_stock_price_uses_valid_cache(self):
        """Test that get_stock_price uses valid cached data."""
        # Mock database session
        mock_db = AsyncMock()

        # Mock cached price entry
        mock_cached_price = Mock()
        mock_cached_price.symbol = "AAPL"
        mock_cached_price.price = 150.0
        mock_cached_price.currency = "USD"
        mock_cached_price.source = "finnhub"
        mock_cached_price.fetched_at = datetime.utcnow() - timedelta(minutes=5)

        with patch(
            "app.crud.crud_price_cache.get_cache_by_symbol"
        ) as mock_get_cache, patch.object(
            cache_management_service, "is_price_cache_valid"
        ) as mock_is_valid, patch.object(
            cache_management_service, "get_price_cache_expiration"
        ) as mock_get_expiration:

            mock_get_cache.return_value = mock_cached_price
            mock_is_valid.return_value = True
            mock_get_expiration.return_value = datetime.utcnow() + timedelta(minutes=10)

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
            mock_is_valid.assert_called_once_with(mock_cached_price)

    @pytest.mark.asyncio
    async def test_get_stock_price_bypasses_cache_on_force_refresh(self):
        """Test that force_refresh bypasses cache completely."""
        mock_db = AsyncMock()

        with patch(
            "app.crud.crud_price_cache.get_cache_by_symbol"
        ) as mock_get_cache, patch.object(
            price_service, "finnhub_client"
        ) as mock_finnhub, patch(
            "app.crud.crud_price_cache.update_or_create_price_cache"
        ) as mock_update_cache:

            # Mock successful API response
            mock_finnhub.quote.return_value = {"c": 155.0}
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


if __name__ == "__main__":
    pytest.main([__file__])
