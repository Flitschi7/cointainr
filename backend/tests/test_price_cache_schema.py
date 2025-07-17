"""
Unit tests for PriceCacheRead schema integration with cache management service.

Tests that the schema methods correctly delegate to the cache management service.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, Mock
from app.schemas.price_cache import PriceCacheRead


class TestPriceCacheReadSchema:
    """Test suite for PriceCacheRead schema cache validation methods."""

    def test_is_cache_valid_delegates_to_service(self):
        """Test that is_cache_valid method delegates to cache management service."""
        # Create a PriceCacheRead instance
        cache_entry = PriceCacheRead(
            id=1,
            symbol="AAPL",
            asset_type="stock",
            price=150.0,
            currency="USD",
            source="finnhub",
            fetched_at=datetime.utcnow() - timedelta(minutes=5),
        )

        with patch(
            "app.services.cache_management.cache_management_service"
        ) as mock_service:
            mock_service.is_price_cache_valid.return_value = True

            result = cache_entry.is_cache_valid()

            assert result is True
            mock_service.is_price_cache_valid.assert_called_once_with(cache_entry)

    def test_get_cache_expiration_delegates_to_service(self):
        """Test that get_cache_expiration method delegates to cache management service."""
        expected_expiration = datetime.utcnow() + timedelta(minutes=15)

        cache_entry = PriceCacheRead(
            id=1,
            symbol="AAPL",
            asset_type="stock",
            price=150.0,
            currency="USD",
            source="finnhub",
            fetched_at=datetime.utcnow(),
        )

        with patch("app.schemas.price_cache.cache_management_service") as mock_service:
            mock_service.get_price_cache_expiration.return_value = expected_expiration

            result = cache_entry.get_cache_expiration()

            assert result == expected_expiration
            mock_service.get_price_cache_expiration.assert_called_once_with(cache_entry)

    def test_get_cache_age_minutes_delegates_to_service(self):
        """Test that get_cache_age_minutes method delegates to cache management service."""
        cache_entry = PriceCacheRead(
            id=1,
            symbol="AAPL",
            asset_type="stock",
            price=150.0,
            currency="USD",
            source="finnhub",
            fetched_at=datetime.utcnow() - timedelta(minutes=10),
        )

        with patch("app.schemas.price_cache.cache_management_service") as mock_service:
            mock_service.get_cache_age_minutes.return_value = 10

            result = cache_entry.get_cache_age_minutes()

            assert result == 10
            mock_service.get_cache_age_minutes.assert_called_once_with(cache_entry)

    def test_schema_methods_with_expired_cache(self):
        """Test schema methods with an expired cache entry."""
        # Create an old cache entry
        cache_entry = PriceCacheRead(
            id=1,
            symbol="AAPL",
            asset_type="stock",
            price=150.0,
            currency="USD",
            source="finnhub",
            fetched_at=datetime.utcnow()
            - timedelta(minutes=30),  # Older than default 15 minutes
        )

        with patch("app.schemas.price_cache.cache_management_service") as mock_service:
            mock_service.is_price_cache_valid.return_value = False
            mock_service.get_cache_expiration.return_value = (
                datetime.utcnow() - timedelta(minutes=15)
            )
            mock_service.get_cache_age_minutes.return_value = 30

            assert cache_entry.is_cache_valid() is False
            assert cache_entry.get_cache_age_minutes() == 30

            expiration = cache_entry.get_cache_expiration()
            assert expiration < datetime.utcnow()  # Should be in the past

    def test_schema_creation_with_all_fields(self):
        """Test that PriceCacheRead can be created with all required fields."""
        cache_entry = PriceCacheRead(
            id=1,
            symbol="BTC",
            asset_type="crypto",
            price=45000.0,
            currency="USD",
            source="coingecko",
            fetched_at=datetime.utcnow(),
        )

        assert cache_entry.id == 1
        assert cache_entry.symbol == "BTC"
        assert cache_entry.asset_type == "crypto"
        assert cache_entry.price == 45000.0
        assert cache_entry.currency == "USD"
        assert cache_entry.source == "coingecko"
        assert isinstance(cache_entry.fetched_at, datetime)


if __name__ == "__main__":
    pytest.main([__file__])
