import pytest
import time
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services.cache_management import CacheManagementService
from app.services.price_service import PriceService
from app.services.conversion_service import ConversionService
from app.models.price_cache import PriceCache
from app.models.conversion_cache import ConversionCache


class TestCacheManagementIntegration:
    """
    Integration tests for the cache management service.
    """

    @pytest.fixture
    def db(self):
        """Get a database session."""
        db = next(get_db())
        yield db
        db.close()

    @pytest.fixture
    def cache_service(self, db):
        """Get a cache management service instance."""
        return CacheManagementService()

    @pytest.fixture
    def price_service(self, db):
        """Get a price service instance."""
        return PriceService()

    @pytest.fixture
    def conversion_service(self, db):
        """Get a conversion service instance."""
        return ConversionService()

    def test_price_cache_lifecycle(self, db, price_service):
        """Test the complete lifecycle of price cache."""
        # 1. Start with a fresh cache entry
        symbol = "AAPL"

        # Force refresh to get a fresh entry
        price_data = price_service.get_stock_price(db, symbol, force_refresh=True)
        assert price_data["cached"] is False

        # 2. Verify that a second request uses cache
        cached_price_data = price_service.get_stock_price(
            db, symbol, force_refresh=False
        )
        assert cached_price_data["cached"] is True

        # 3. Force refresh again to bypass cache
        fresh_price_data = price_service.get_stock_price(db, symbol, force_refresh=True)
        assert fresh_price_data["cached"] is False

        # 4. Clear the cache
        db.query(PriceCache).filter(PriceCache.symbol == symbol).delete()
        db.commit()

        # 5. Verify that a new request doesn't use cache
        new_price_data = price_service.get_stock_price(db, symbol, force_refresh=False)
        assert new_price_data["cached"] is False

    def test_conversion_cache_lifecycle(self, db, conversion_service):
        """Test the complete lifecycle of conversion cache."""
        # 1. Start with a fresh cache entry
        from_currency = "USD"
        to_currency = "EUR"

        # Force refresh to get a fresh entry
        conversion_data = conversion_service.get_conversion_rate(
            db, from_currency, to_currency, force_refresh=True
        )
        assert conversion_data["cached"] is False

        # 2. Verify that a second request uses cache
        cached_conversion_data = conversion_service.get_conversion_rate(
            db, from_currency, to_currency, force_refresh=False
        )
        assert cached_conversion_data["cached"] is True

        # 3. Force refresh again to bypass cache
        fresh_conversion_data = conversion_service.get_conversion_rate(
            db, from_currency, to_currency, force_refresh=True
        )
        assert fresh_conversion_data["cached"] is False

        # 4. Clear the cache
        db.query(ConversionCache).filter(
            ConversionCache.from_currency == from_currency,
            ConversionCache.to_currency == to_currency,
        ).delete()
        db.commit()

        # 5. Verify that a new request doesn't use cache
        new_conversion_data = conversion_service.get_conversion_rate(
            db, from_currency, to_currency, force_refresh=False
        )
        assert new_conversion_data["cached"] is False

    def test_cache_ttl_settings(self, db, cache_service):
        """Test that cache TTL settings are respected."""
        # Create a mock price cache entry with a timestamp in the past
        symbol = "TEST_TTL"
        price = 100.0
        currency = "USD"

        # Create an entry that's just expired
        price_cache = PriceCache(
            symbol=symbol,
            price=price,
            currency=currency,
            timestamp=datetime.now() - timedelta(minutes=16),  # Assuming 15 min TTL
        )
        db.add(price_cache)
        db.commit()

        # Check if the cache service considers it expired
        cache_valid = cache_service.is_price_cache_valid(price_cache)
        assert cache_valid is False

        # Create a fresh entry
        fresh_price_cache = PriceCache(
            symbol=symbol + "_FRESH",
            price=price,
            currency=currency,
            timestamp=datetime.now(),
        )
        db.add(fresh_price_cache)
        db.commit()

        # Check if the cache service considers it valid
        fresh_cache_valid = cache_service.is_price_cache_valid(fresh_price_cache)
        assert fresh_cache_valid is True

        # Clean up
        db.query(PriceCache).filter(
            PriceCache.symbol.in_([symbol, symbol + "_FRESH"])
        ).delete()
        db.commit()

    def test_cache_stats(self, db, cache_service, price_service):
        """Test that cache statistics are accurate."""
        # Add some test data
        symbols = ["STAT1", "STAT2", "STAT3"]

        # Clear existing entries for these symbols
        db.query(PriceCache).filter(PriceCache.symbol.in_(symbols)).delete()
        db.commit()

        # Create entries with different timestamps
        now = datetime.now()

        # Fresh entry
        db.add(
            PriceCache(
                symbol=symbols[0],
                price=100.0,
                currency="USD",
                timestamp=now,
                asset_type="stock",
            )
        )

        # Slightly old entry
        db.add(
            PriceCache(
                symbol=symbols[1],
                price=200.0,
                currency="USD",
                timestamp=now - timedelta(minutes=10),
                asset_type="stock",
            )
        )

        # Expired entry
        db.add(
            PriceCache(
                symbol=symbols[2],
                price=300.0,
                currency="USD",
                timestamp=now - timedelta(minutes=20),
                asset_type="crypto",
            )
        )

        db.commit()

        # Get cache stats
        stats = cache_service.get_price_cache_stats(db)

        # Check that stats are accurate
        assert stats["total_entries"] >= 3  # There might be other entries
        assert stats["stock_entries"] >= 2
        assert stats["crypto_entries"] >= 1
        assert stats["fresh_entries"] >= 2  # The first two should be fresh

        # Clean up
        db.query(PriceCache).filter(PriceCache.symbol.in_(symbols)).delete()
        db.commit()
