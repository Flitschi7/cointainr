"""
Tests for cache expiration scenarios and force refresh behavior.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, AsyncMock
from app.services.cache_management import CacheManagementService, get_utc_now
from app.models.price_cache import PriceCache
from app.models.conversion_cache import ConversionCache
from sqlalchemy import select


class TestCacheExpiration:
    """Test suite for cache expiration scenarios."""

    @pytest.fixture
    def cache_service(self):
        """Create a CacheManagementService instance."""
        return CacheManagementService()

    @pytest.mark.asyncio
    async def test_price_cache_expiration_edge_cases(self, cache_service):
        """Test price cache expiration edge cases."""
        # Test case 1: Cache that expires exactly at TTL
        mock_entry = Mock()
        mock_entry.fetched_at = get_utc_now() - timedelta(
            minutes=15
        )  # Exactly 15 minutes old

        # Should be valid at exactly TTL
        assert cache_service.is_price_cache_valid(mock_entry) is True

        # Test case 2: Cache that expires just after TTL
        mock_entry.fetched_at = get_utc_now() - timedelta(
            minutes=15, seconds=1
        )  # 15 minutes and 1 second old

        # Should be invalid just after TTL
        assert cache_service.is_price_cache_valid(mock_entry) is False

        # Test case 3: Cache that expires just before TTL
        mock_entry.fetched_at = get_utc_now() - timedelta(
            minutes=14, seconds=59
        )  # 14 minutes and 59 seconds old

        # Should be valid just before TTL
        assert cache_service.is_price_cache_valid(mock_entry) is True

    @pytest.mark.asyncio
    async def test_conversion_cache_expiration_edge_cases(self, cache_service):
        """Test conversion cache expiration edge cases."""
        # Test case 1: Cache that expires exactly at TTL
        mock_entry = Mock()
        mock_entry.fetched_at = get_utc_now() - timedelta(
            hours=8
        )  # Exactly 8 hours old

        # Should be valid at exactly TTL
        assert cache_service.is_conversion_cache_valid(mock_entry) is True

        # Test case 2: Cache that expires just after TTL
        mock_entry.fetched_at = get_utc_now() - timedelta(
            hours=8, minutes=1
        )  # 8 hours and 1 minute old

        # Should be invalid just after TTL
        assert cache_service.is_conversion_cache_valid(mock_entry) is False

        # Test case 3: Cache that expires just before TTL
        mock_entry.fetched_at = get_utc_now() - timedelta(
            hours=7, minutes=59
        )  # 7 hours and 59 minutes old

        # Should be valid just before TTL
        assert cache_service.is_conversion_cache_valid(mock_entry) is True

    @pytest.mark.asyncio
    async def test_force_refresh_behavior_price_cache(self, cache_service):
        """Test force refresh behavior for price cache."""
        # Create a valid cache entry
        mock_entry = Mock()
        mock_entry.fetched_at = get_utc_now() - timedelta(
            minutes=5
        )  # 5 minutes old, well within TTL

        # Should be valid without force refresh
        assert cache_service.is_price_cache_valid(mock_entry) is True

        # Should be invalid with force refresh, regardless of age
        assert (
            cache_service.is_price_cache_valid(mock_entry, force_refresh=True) is False
        )

        # Test with a brand new cache entry
        mock_entry.fetched_at = get_utc_now()  # Just created

        # Should still be invalid with force refresh
        assert (
            cache_service.is_price_cache_valid(mock_entry, force_refresh=True) is False
        )

    @pytest.mark.asyncio
    async def test_force_refresh_behavior_conversion_cache(self, cache_service):
        """Test force refresh behavior for conversion cache."""
        # Create a valid cache entry
        mock_entry = Mock()
        mock_entry.fetched_at = get_utc_now() - timedelta(
            hours=1
        )  # 1 hour old, well within TTL

        # Should be valid without force refresh
        assert cache_service.is_conversion_cache_valid(mock_entry) is True

        # Should be invalid with force refresh, regardless of age
        assert (
            cache_service.is_conversion_cache_valid(mock_entry, force_refresh=True)
            is False
        )

        # Test with a brand new cache entry
        mock_entry.fetched_at = get_utc_now()  # Just created

        # Should still be invalid with force refresh
        assert (
            cache_service.is_conversion_cache_valid(mock_entry, force_refresh=True)
            is False
        )

    @pytest.mark.asyncio
    async def test_custom_ttl_settings(self):
        """Test cache validation with custom TTL settings."""
        # Create service with custom TTL settings
        with patch("app.services.cache_management.settings") as mock_settings:
            mock_settings.PRICE_CACHE_MINUTES = 30  # Longer TTL
            mock_settings.CONVERSION_CACHE_HOURS = 12  # Longer TTL

            custom_service = CacheManagementService()

            # Test price cache with custom TTL
            mock_entry = Mock()
            mock_entry.fetched_at = get_utc_now() - timedelta(
                minutes=25
            )  # 25 minutes old

            # Should be valid with 30-minute TTL
            assert custom_service.is_price_cache_valid(mock_entry) is True

            # Test conversion cache with custom TTL
            mock_entry.fetched_at = get_utc_now() - timedelta(hours=10)  # 10 hours old

            # Should be valid with 12-hour TTL
            assert custom_service.is_conversion_cache_valid(mock_entry) is True

    @pytest.mark.asyncio
    async def test_cache_status_with_force_refresh(self, cache_service):
        """Test cache status reporting with force refresh."""
        # Create a valid cache entry
        mock_entry = Mock()
        mock_entry.fetched_at = get_utc_now() - timedelta(minutes=5)  # 5 minutes old

        # Get cache status without force refresh
        status_normal = cache_service.get_cache_status(mock_entry, 15)

        # Get cache status with force refresh
        status_forced = cache_service.get_cache_status(
            mock_entry, 15, force_refresh=True
        )

        # Normal status should show valid cache
        assert status_normal["is_valid"] is True
        assert status_normal["force_refresh_requested"] is False

        # Forced status should show invalid cache due to force refresh
        assert status_forced["is_valid"] is False
        assert status_forced["force_refresh_requested"] is True

        # Both should have the same cache age
        assert status_normal["cache_age_minutes"] == status_forced["cache_age_minutes"]
