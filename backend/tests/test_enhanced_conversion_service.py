import asyncio
import sys
import os
from datetime import datetime

# Add the parent directory to sys.path to allow imports from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.conversion_service import conversion_service
from app.db.session import SessionLocal
from app.core.config import settings


async def test_conversion_service():
    """
    Test the enhanced conversion service with various scenarios.
    """
    print("\n=== Testing Enhanced Conversion Service ===\n")

    # Get a database session
    async with SessionLocal() as db:
        try:
            # Test 1: Same currency conversion (USD to USD)
            print("Test 1: Same currency conversion (USD to USD)")
            result = await conversion_service.get_conversion_rate(db, "USD", "USD")
            print(f"Rate: {result['rate']}")
            print(f"Cached: {result['cached']}")
            print(f"Source: {result['source']}")
            print(f"Cache status: {result['cache_status']}")
            print("\n" + "-" * 50 + "\n")

            # Test 2: Direct currency pair with caching (USD to EUR)
            print("Test 2: Direct currency pair (USD to EUR) - First call (API)")
            result1 = await conversion_service.get_conversion_rate(db, "USD", "EUR")
            print(f"Rate: {result1['rate']}")
            print(f"Cached: {result1['cached']}")
            print(f"Source: {result1['source']}")
            print(f"Cache status: {result1['cache_status']}")
            print("\n" + "-" * 50 + "\n")

            print(
                "Test 2b: Direct currency pair (USD to EUR) - Second call (should use cache)"
            )
            result2 = await conversion_service.get_conversion_rate(db, "USD", "EUR")
            print(f"Rate: {result2['rate']}")
            print(f"Cached: {result2['cached']}")
            print(f"Source: {result2['source']}")
            print(f"Cache status: {result2['cache_status']}")
            print("\n" + "-" * 50 + "\n")

            # Test 3: Inverse currency pair (EUR to USD - should use cached USD to EUR)
            print(
                "Test 3: Inverse currency pair (EUR to USD - should use cached USD to EUR)"
            )
            result3 = await conversion_service.get_conversion_rate(db, "EUR", "USD")
            print(f"Rate: {result3['rate']}")
            print(f"Cached: {result3['cached']}")
            print(f"Source: {result3['source']}")
            print(f"Cache status: {result3['cache_status']}")
            print(f"Is inverse pair: {result3['cache_status']['is_inverse_pair']}")
            print("\n" + "-" * 50 + "\n")

            # Test 4: Force refresh to bypass cache
            print("Test 4: Force refresh to bypass cache (USD to EUR)")
            result4 = await conversion_service.get_conversion_rate(
                db, "USD", "EUR", force_refresh=True
            )
            print(f"Rate: {result4['rate']}")
            print(f"Cached: {result4['cached']}")
            print(f"Source: {result4['source']}")
            print(f"Cache status: {result4['cache_status']}")
            print("\n" + "-" * 50 + "\n")

            # Test 5: Convert amount with caching
            print("Test 5: Convert amount with caching (100 USD to EUR)")
            result5 = await conversion_service.convert_amount(db, "USD", "EUR", 100)
            print(f"Amount: {result5['amount']} {result5['from']}")
            print(f"Converted: {result5['converted']} {result5['to']}")
            print(f"Rate: {result5['rate']}")
            print(f"Cached: {result5['cached']}")
            print(f"Cache status: {result5['cache_status']}")

        except Exception as e:
            print(f"Error during test: {e}")


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_conversion_service())
