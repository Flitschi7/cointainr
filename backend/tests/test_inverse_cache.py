import asyncio
import sys
import os
from datetime import datetime

# Add the parent directory to sys.path to allow imports from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.conversion_service import conversion_service
from app.db.session import SessionLocal
from app.core.config import settings
from app.crud import crud_conversion_cache


async def test_inverse_cache():
    """
    Test the inverse currency pair caching feature.
    """
    print("\n=== Testing Inverse Currency Pair Caching ===\n")

    # Get a database session
    async with SessionLocal() as db:
        try:
            # First, clear all conversion cache entries
            print("Clearing all conversion cache entries...")
            cleared = await crud_conversion_cache.cleanup_old_conversion_cache_entries(
                db, max_age_days=0
            )
            print(f"Cleared {cleared} cache entries")
            print("\n" + "-" * 50 + "\n")

            # Test 1: Get USD to EUR rate (should fetch from API)
            print("Test 1: Get USD to EUR rate (should fetch from API)")
            result1 = await conversion_service.get_conversion_rate(db, "USD", "EUR")
            print(f"Rate: {result1['rate']}")
            print(f"Cached: {result1['cached']}")
            print(f"Source: {result1['source']}")
            print(f"Cache status: {result1['cache_status']}")
            print("\n" + "-" * 50 + "\n")

            # Test 2: Get EUR to USD rate (should use inverse of cached USD to EUR)
            print(
                "Test 2: Get EUR to USD rate (should use inverse of cached USD to EUR)"
            )
            result2 = await conversion_service.get_conversion_rate(db, "EUR", "USD")
            print(f"Rate: {result2['rate']}")
            print(f"Cached: {result2['cached']}")
            print(f"Source: {result2['source']}")
            print(f"Cache status: {result2['cache_status']}")
            print(f"Is inverse pair: {result2['cache_status']['is_inverse_pair']}")

            # Verify that the rate is approximately the inverse
            usd_eur_rate = result1["rate"]
            eur_usd_rate = result2["rate"]
            expected_inverse = 1.0 / usd_eur_rate
            print(f"\nVerification:")
            print(f"USD to EUR rate: {usd_eur_rate}")
            print(f"EUR to USD rate: {eur_usd_rate}")
            print(f"Expected inverse: {expected_inverse}")
            print(f"Difference: {abs(eur_usd_rate - expected_inverse)}")
            print(
                f"Is approximately inverse: {abs(eur_usd_rate - expected_inverse) < 0.0001}"
            )

        except Exception as e:
            print(f"Error during test: {e}")


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_inverse_cache())
