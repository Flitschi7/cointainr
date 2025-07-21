"""
Unit tests for enhanced ConversionService with centralized cache management.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, Mock
from app.services.conversion_service import ConversionService
from app.services.cache_management import CacheManagementService
from app.models.conversion_cache import ConversionCache


class TestEnhancedConversionService:
    """Test suite for enhanced ConversionService caching behavior."""

    @pytest.fixture
    def conversion_service(self):
        """Create a ConversionService instance with mocked dependencies."""
        cache_service = CacheManagementService()
        return ConversionService(cache_service=cache_service)

    @pytest.mark.asyncio
    async def test_same_currency_conversion(self, conversion_service):
        """Test conversion between same currencies (USD to USD)."""
        mock_db = AsyncMock()

        result = await conversion_service.get_conversion_rate(mock_db, "USD", "USD")

        assert result["rate"] == 1.0
        assert result["from_currency"] == "USD"
        assert result["to_currency"] == "USD"
        assert result["cached"] is True
        assert result["source"] == "internal"
        assert "cache_status" in result

    @pytest.mark.asyncio
    async def test_get_conversion_rate_uses_valid_cache(self, conversion_service):
        """Test that get_conversion_rate uses valid cached data."""
        mock_db = AsyncMock()

        # Mock cached conversion entry
        mock_cached_conversion = Mock(spec=ConversionCache)
        mock_cached_conversion.from_currency = "USD"
        mock_cached_conversion.to_currency = "EUR"
        mock_cached_conversion.rate = 0.85
        mock_cached_conversion.source = "exchangerate-api"
        mock_cached_conversion.fetched_at = datetime.now(timezone.utc) - timedelta(
            hours=1
        )

        with patch(
            "app.crud.crud_conversion_cache.get_conversion_rate"
        ) as mock_get_cache, patch.object(
            CacheManagementService, "is_conversion_cache_valid"
        ) as mock_is_valid, patch.object(
            CacheManagementService, "get_conversion_cache_expiration"
        ) as mock_get_expiration:

            mock_get_cache.return_value = mock_cached_conversion
            mock_is_valid.return_value = True
            mock_get_expiration.return_value = datetime.now(timezone.utc) + timedelta(
                hours=7
            )

            result = await conversion_service.get_conversion_rate(
                mock_db, "USD", "EUR", force_refresh=False
            )

            assert result["from_currency"] == "USD"
            assert result["to_currency"] == "EUR"
            assert result["rate"] == 0.85
            assert result["cached"] is True
            assert "cache_valid_until" in result
            mock_get_cache.assert_called_once_with(
                db=mock_db, from_currency="USD", to_currency="EUR"
            )
            mock_is_valid.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_conversion_rate_bypasses_cache_on_force_refresh(
        self, conversion_service
    ):
        """Test that force_refresh bypasses cache completely."""
        mock_db = AsyncMock()

        with patch(
            "app.crud.crud_conversion_cache.get_conversion_rate"
        ) as mock_get_cache, patch.object(
            conversion_service, "_fetch_conversion_rate", new_callable=AsyncMock
        ) as mock_fetch_rate, patch(
            "app.crud.crud_conversion_cache.update_or_create_conversion_rate",
            new_callable=AsyncMock,
        ) as mock_update_cache:

            # Mock successful API response
            mock_fetch_rate.return_value = {
                "from_currency": "USD",
                "to_currency": "EUR",
                "rate": 0.85,
                "source": "exchangerate-api",
                "timestamp": datetime.now(timezone.utc),
            }
            mock_update_cache.return_value = Mock()

            result = await conversion_service.get_conversion_rate(
                mock_db, "USD", "EUR", force_refresh=True
            )

            assert result["from_currency"] == "USD"
            assert result["to_currency"] == "EUR"
            assert result["rate"] == 0.85
            assert result["cached"] is False
            assert "cache_valid_until" in result
            # Cache should not be checked when force_refresh=True
            mock_get_cache.assert_not_called()
            mock_fetch_rate.assert_called_once_with(mock_db, "USD", "EUR")

    @pytest.mark.asyncio
    async def test_inverse_currency_pair_handling(self, conversion_service):
        """Test handling of inverse currency pairs."""
        mock_db = AsyncMock()

        # Mock cached conversion entry for USD to EUR
        mock_cached_conversion = Mock(spec=ConversionCache)
        mock_cached_conversion.from_currency = "USD"
        mock_cached_conversion.to_currency = "EUR"
        mock_cached_conversion.rate = 0.85
        mock_cached_conversion.source = "exchangerate-api"
        mock_cached_conversion.fetched_at = datetime.now(timezone.utc) - timedelta(
            hours=1
        )

        with patch(
            "app.crud.crud_conversion_cache.get_conversion_rate"
        ) as mock_get_cache, patch.object(
            CacheManagementService, "is_conversion_cache_valid"
        ) as mock_is_valid:

            # First call returns None (no direct EUR to USD cache)
            # Second call returns USD to EUR cache
            mock_get_cache.side_effect = [None, mock_cached_conversion]
            mock_is_valid.return_value = True

            result = await conversion_service.get_conversion_rate(
                mock_db, "EUR", "USD", force_refresh=False
            )

            assert result["from_currency"] == "EUR"
            assert result["to_currency"] == "USD"
            # Inverse of 0.85 is approximately 1.176
            assert round(result["rate"], 3) == round(1 / 0.85, 3)
            assert result["cached"] is True
            assert result["cache_status"]["is_inverse_pair"] is True

            # Should have been called twice - once for EUR->USD, once for USD->EUR
            assert mock_get_cache.call_count == 2

    @pytest.mark.asyncio
    async def test_convert_amount(self, conversion_service):
        """Test the convert_amount method."""
        mock_db = AsyncMock()

        # Mock the get_conversion_rate method
        with patch.object(
            conversion_service, "get_conversion_rate", new_callable=AsyncMock
        ) as mock_get_rate:

            mock_get_rate.return_value = {
                "from_currency": "USD",
                "to_currency": "EUR",
                "rate": 0.85,
                "cached": True,
                "source": "exchangerate-api",
                "cache_status": {"is_valid": True},
            }

            result = await conversion_service.convert_amount(
                mock_db, "USD", "EUR", 100.0
            )

            assert result["from"] == "USD"
            assert result["to"] == "EUR"
            assert result["amount"] == 100.0
            assert result["converted"] == 85.0  # 100 * 0.85
            assert result["rate"] == 0.85
            assert result["cached"] is True

            mock_get_rate.assert_called_once_with(
                mock_db, "USD", "EUR", force_refresh=False
            )
