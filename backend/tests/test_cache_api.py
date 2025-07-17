import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.cache_management import CacheManagementService
from app.services.price_service import PriceService
from app.services.conversion_service import ConversionService

client = TestClient(app)


class TestCacheAPI:
    """
    Integration tests for the cache-related API endpoints.
    """

    def test_get_asset_cache_status(self):
        """Test that the asset cache status endpoint returns valid data."""
        response = client.get("/api/v1/price/cache/asset-status")
        assert response.status_code == 200
        data = response.json()

        # Check that the response is a list
        assert isinstance(data, list)

        # If there are any items, check their structure
        if data:
            item = data[0]
            assert "asset_id" in item
            assert "symbol" in item
            assert "type" in item
            assert "cached_at" in item
            assert "cache_ttl_minutes" in item

    def test_get_cache_stats(self):
        """Test that the cache stats endpoint returns valid data."""
        response = client.get("/api/v1/price/cache/stats")
        assert response.status_code == 200
        data = response.json()

        # Check that the response has the expected fields
        assert "total_entries" in data
        assert "fresh_entries" in data
        assert "stock_entries" in data
        assert "crypto_entries" in data
        assert "cache_age_minutes" in data

    def test_get_conversion_cache_stats(self):
        """Test that the conversion cache stats endpoint returns valid data."""
        response = client.get("/api/v1/conversion/cache/stats")
        assert response.status_code == 200
        data = response.json()

        # Check that the response has the expected fields
        assert "total_entries" in data
        assert "fresh_entries" in data
        assert "cache_age_hours" in data

    def test_clear_price_cache(self):
        """Test that the clear price cache endpoint works."""
        response = client.post("/api/v1/price/cache/clear")
        assert response.status_code == 200
        data = response.json()

        # Check that the response indicates success
        assert "success" in data
        assert data["success"] is True
        assert "cleared_entries" in data

    def test_clear_conversion_cache(self):
        """Test that the clear conversion cache endpoint works."""
        response = client.post("/api/v1/conversion/cache/clear")
        assert response.status_code == 200
        data = response.json()

        # Check that the response indicates success
        assert "success" in data
        assert data["success"] is True
        assert "cleared_entries" in data

    def test_refresh_all_prices_respects_force_refresh(self):
        """Test that the refresh-all endpoint respects the force_refresh parameter."""
        # First call without force_refresh
        response1 = client.post(
            "/api/v1/price/refresh-all", json={"force_refresh": False}
        )
        assert response1.status_code == 200
        data1 = response1.json()

        # Check that the response has the expected fields
        assert "refreshed" in data1
        assert "errors" in data1
        assert "cached" in data1

        # Then call with force_refresh
        response2 = client.post(
            "/api/v1/price/refresh-all", json={"force_refresh": True}
        )
        assert response2.status_code == 200
        data2 = response2.json()

        # The second call should have fewer or equal cached items
        # since we're forcing refresh
        assert data2["cached"] <= data1["cached"]

    def test_get_stock_price_respects_cache(self):
        """Test that the stock price endpoint respects cache."""
        # First call to ensure we have cached data
        symbol = "AAPL"  # Use a common stock symbol
        response1 = client.get(f"/api/v1/price/stock/{symbol}")
        assert response1.status_code == 200

        # Second call without force_refresh should use cache
        response2 = client.get(f"/api/v1/price/stock/{symbol}?force_refresh=false")
        assert response2.status_code == 200
        data2 = response2.json()

        # Check that it used cache
        assert data2["cached"] is True

        # Third call with force_refresh should bypass cache
        response3 = client.get(f"/api/v1/price/stock/{symbol}?force_refresh=true")
        assert response3.status_code == 200
        data3 = response3.json()

        # Check that it didn't use cache
        assert data3["cached"] is False

    def test_get_crypto_price_respects_cache(self):
        """Test that the crypto price endpoint respects cache."""
        # First call to ensure we have cached data
        symbol = "BTC"  # Use a common crypto symbol
        response1 = client.get(f"/api/v1/price/crypto/{symbol}")
        assert response1.status_code == 200

        # Second call without force_refresh should use cache
        response2 = client.get(f"/api/v1/price/crypto/{symbol}?force_refresh=false")
        assert response2.status_code == 200
        data2 = response2.json()

        # Check that it used cache
        assert data2["cached"] is True

        # Third call with force_refresh should bypass cache
        response3 = client.get(f"/api/v1/price/crypto/{symbol}?force_refresh=true")
        assert response3.status_code == 200
        data3 = response3.json()

        # Check that it didn't use cache
        assert data3["cached"] is False

    def test_get_conversion_rate_respects_cache(self):
        """Test that the conversion rate endpoint respects cache."""
        # First call to ensure we have cached data
        from_currency = "USD"
        to_currency = "EUR"
        response1 = client.get(
            f"/api/v1/conversion/rate?from={from_currency}&to={to_currency}"
        )
        assert response1.status_code == 200

        # Second call without force_refresh should use cache
        response2 = client.get(
            f"/api/v1/conversion/rate?from={from_currency}&to={to_currency}&force_refresh=false"
        )
        assert response2.status_code == 200
        data2 = response2.json()

        # Check that it used cache
        assert data2["cached"] is True

        # Third call with force_refresh should bypass cache
        response3 = client.get(
            f"/api/v1/conversion/rate?from={from_currency}&to={to_currency}&force_refresh=true"
        )
        assert response3.status_code == 200
        data3 = response3.json()

        # Check that it didn't use cache
        assert data3["cached"] is False
