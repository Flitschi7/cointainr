"""
Unit tests for the CacheManagementService.

Tests cache validation logic, expiration calculations, and settings handling.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from app.services.cache_management import CacheManagementService


class TestCacheManagementService:
    """Test suite for CacheManagementService."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.service = CacheManagementService()

    def test_init_with_default_settings(self):
        """Test that service initializes with correct default settings."""
        # Mock settings to test default behavior
        with patch("app.services.cache_management.settings") as mock_settings:
            mock_settings.PRICE_CACHE_MINUTES = 15
            mock_settings.CONVERSION_CACHE_HOURS = 8

            service = CacheManagementService()
            assert service._price_cache_minutes == 15
            assert service._conversion_cache_hours == 8

    def test_is_price_cache_valid_with_valid_cache(self):
        """Test price cache validation with valid cache entry."""
        # Create mock cache entry with recent timestamp
        mock_entry = Mock()
        mock_entry.fetched_at = datetime.utcnow() - timedelta(minutes=10)

        # Should be valid since it's within 15 minutes default
        assert self.service.is_price_cache_valid(mock_entry) is True

    def test_is_price_cache_valid_with_expired_cache(self):
        """Test price cache validation with expired cache entry."""
        # Create mock cache entry with old timestamp
        mock_entry = Mock()
        mock_entry.fetched_at = datetime.utcnow() - timedelta(minutes=20)

        # Should be invalid since it's older than 15 minutes default
        assert self.service.is_price_cache_valid(mock_entry) is False

    def test_is_price_cache_valid_with_none_entry(self):
        """Test price cache validation with None entry."""
        assert self.service.is_price_cache_valid(None) is False

    def test_is_price_cache_valid_with_no_fetched_at(self):
        """Test price cache validation with entry missing fetched_at."""
        mock_entry = Mock()
        mock_entry.fetched_at = None

        assert self.service.is_price_cache_valid(mock_entry) is False

    def test_is_price_cache_valid_with_missing_attribute(self):
        """Test price cache validation with entry missing fetched_at attribute."""
        mock_entry = Mock(spec=[])  # Mock with no attributes

        assert self.service.is_price_cache_valid(mock_entry) is False

    def test_is_conversion_cache_valid_with_valid_cache(self):
        """Test conversion cache validation with valid cache entry."""
        # Create mock cache entry with recent timestamp (within 8 hours)
        mock_entry = Mock()
        mock_entry.fetched_at = datetime.utcnow() - timedelta(hours=4)

        # Should be valid since it's within 8 hours default
        assert self.service.is_conversion_cache_valid(mock_entry) is True

    def test_is_conversion_cache_valid_with_expired_cache(self):
        """Test conversion cache validation with expired cache entry."""
        # Create mock cache entry with old timestamp (older than 8 hours)
        mock_entry = Mock()
        mock_entry.fetched_at = datetime.utcnow() - timedelta(hours=10)

        # Should be invalid since it's older than 8 hours default
        assert self.service.is_conversion_cache_valid(mock_entry) is False

    def test_is_conversion_cache_valid_with_none_entry(self):
        """Test conversion cache validation with None entry."""
        assert self.service.is_conversion_cache_valid(None) is False

    def test_get_price_cache_expiration_valid_entry(self):
        """Test price cache expiration calculation with valid entry."""
        base_time = datetime.utcnow()
        mock_entry = Mock()
        mock_entry.fetched_at = base_time

        expected_expiration = base_time + timedelta(minutes=15)  # Default setting
        actual_expiration = self.service.get_price_cache_expiration(mock_entry)

        # Allow small time difference due to test execution time
        assert abs((actual_expiration - expected_expiration).total_seconds()) < 1

    def test_get_price_cache_expiration_none_entry(self):
        """Test price cache expiration calculation with None entry."""
        assert self.service.get_price_cache_expiration(None) is None

    def test_get_conversion_cache_expiration_valid_entry(self):
        """Test conversion cache expiration calculation with valid entry."""
        base_time = datetime.utcnow()
        mock_entry = Mock()
        mock_entry.fetched_at = base_time

        expected_expiration = base_time + timedelta(hours=8)  # Default setting
        actual_expiration = self.service.get_conversion_cache_expiration(mock_entry)

        # Allow small time difference due to test execution time
        assert abs((actual_expiration - expected_expiration).total_seconds()) < 1

    def test_get_conversion_cache_expiration_none_entry(self):
        """Test conversion cache expiration calculation with None entry."""
        assert self.service.get_conversion_cache_expiration(None) is None

    def test_get_cache_age_minutes_valid_entry(self):
        """Test cache age calculation with valid entry."""
        # Create entry that's 30 minutes old
        mock_entry = Mock()
        mock_entry.fetched_at = datetime.utcnow() - timedelta(minutes=30)

        age = self.service.get_cache_age_minutes(mock_entry)

        # Should be approximately 30 minutes (allow small variance)
        assert 29 <= age <= 31

    def test_get_cache_age_minutes_none_entry(self):
        """Test cache age calculation with None entry."""
        assert self.service.get_cache_age_minutes(None) is None

    def test_get_cache_settings(self):
        """Test getting current cache settings."""
        with patch("app.services.cache_management.settings") as mock_settings:
            mock_settings.PRICE_CACHE_MINUTES = 20
            mock_settings.CONVERSION_CACHE_HOURS = 12
            mock_settings.PRICE_CACHE_CLEANUP_DAYS = 5
            mock_settings.CONVERSION_CACHE_CLEANUP_DAYS = 10

            service = CacheManagementService()
            settings = service.get_cache_settings()

            expected = {
                "price_cache_minutes": 20,
                "conversion_cache_hours": 12,
                "price_cache_cleanup_days": 5,
                "conversion_cache_cleanup_days": 10,
            }

            assert settings == expected

    @pytest.mark.asyncio
    async def test_get_cache_status_for_assets_empty_list(self):
        """Test cache status retrieval with empty asset list."""
        mock_db = AsyncMock()

        result = await self.service.get_cache_status_for_assets(mock_db, [])

        assert result == []

    @pytest.mark.asyncio
    async def test_get_cache_status_for_assets_with_valid_cache(self):
        """Test cache status retrieval with assets having valid cache."""
        mock_db = AsyncMock()

        # Mock cached entry
        mock_cached_entry = Mock()
        mock_cached_entry.fetched_at = datetime.utcnow() - timedelta(minutes=5)

        assets = [{"id": 1, "symbol": "AAPL", "type": "stock"}]

        with patch(
            "app.crud.crud_price_cache.get_cached_price", new_callable=AsyncMock
        ) as mock_get_cached_price:
            mock_get_cached_price.return_value = mock_cached_entry

            result = await self.service.get_cache_status_for_assets(mock_db, assets)

            assert len(result) == 1
            status = result[0]
            assert status["asset_id"] == 1
            assert status["symbol"] == "AAPL"
            assert status["type"] == "stock"
            assert status["is_valid"] is True
            assert status["cached_at"] is not None
            assert status["expires_at"] is not None
            assert status["cache_ttl_minutes"] == 15

    @pytest.mark.asyncio
    async def test_get_cache_status_for_assets_with_no_cache(self):
        """Test cache status retrieval with assets having no cache."""
        mock_db = AsyncMock()

        assets = [{"id": 1, "symbol": "AAPL", "type": "stock"}]

        with patch(
            "app.crud.crud_price_cache.get_cached_price", new_callable=AsyncMock
        ) as mock_get_cached_price:
            mock_get_cached_price.return_value = None

            result = await self.service.get_cache_status_for_assets(mock_db, assets)

            assert len(result) == 1
            status = result[0]
            assert status["asset_id"] == 1
            assert status["symbol"] == "AAPL"
            assert status["type"] == "stock"
            assert status["is_valid"] is False
            assert status["cached_at"] is None
            assert status["expires_at"] is None

    @pytest.mark.asyncio
    async def test_get_cache_status_for_assets_with_invalid_asset(self):
        """Test cache status retrieval with invalid asset data."""
        mock_db = AsyncMock()

        # Asset missing required fields
        assets = [
            {"id": 1, "symbol": "AAPL"},  # Missing 'type'
            {"symbol": "GOOGL", "type": "stock"},  # Missing 'id'
            {},  # Missing all fields
        ]

        result = await self.service.get_cache_status_for_assets(mock_db, assets)

        # Should return empty list since all assets are invalid
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_cache_status_for_assets_with_exception(self):
        """Test cache status retrieval handles exceptions gracefully."""
        mock_db = AsyncMock()

        assets = [{"id": 1, "symbol": "AAPL", "type": "stock"}]

        with patch(
            "app.crud.crud_price_cache.get_cached_price", new_callable=AsyncMock
        ) as mock_get_cached_price:
            mock_get_cached_price.side_effect = Exception("Database error")

            # Should not raise exception, but return status with defaults
            result = await self.service.get_cache_status_for_assets(mock_db, assets)

            assert len(result) == 1
            status = result[0]
            assert status["asset_id"] == 1
            assert status["is_valid"] is False

    def test_is_cache_valid_internal_method(self):
        """Test internal _is_cache_valid method."""
        base_time = datetime.utcnow()

        # Test valid cache (within time limit)
        recent_time = base_time - timedelta(minutes=10)
        assert self.service._is_cache_valid(recent_time, 15) is True

        # Test expired cache (beyond time limit)
        old_time = base_time - timedelta(minutes=20)
        assert self.service._is_cache_valid(old_time, 15) is False

        # Test edge case (exactly at limit)
        edge_time = base_time - timedelta(minutes=15)
        assert self.service._is_cache_valid(edge_time, 15) is True

        # Test with None timestamp
        assert self.service._is_cache_valid(None, 15) is False

    def test_custom_cache_settings(self):
        """Test service with custom cache settings from environment."""
        with patch("app.services.cache_management.settings") as mock_settings:
            mock_settings.PRICE_CACHE_MINUTES = 30
            mock_settings.CONVERSION_CACHE_HOURS = 12

            service = CacheManagementService()

            # Test with custom settings
            mock_entry = Mock()
            mock_entry.fetched_at = datetime.utcnow() - timedelta(minutes=25)

            # Should be valid with 30-minute setting
            assert service.is_price_cache_valid(mock_entry) is True

            # Test conversion with 12-hour setting
            mock_entry.fetched_at = datetime.utcnow() - timedelta(hours=10)
            assert service.is_conversion_cache_valid(mock_entry) is True


if __name__ == "__main__":
    pytest.main([__file__])
