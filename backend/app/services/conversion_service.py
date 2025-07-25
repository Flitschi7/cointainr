from sqlalchemy.ext.asyncio import AsyncSession
from app.crud import crud_conversion_cache
from app.core.config import settings
from app.services.cache_management import cache_management_service
import httpx
from typing import Dict, Optional, Tuple
from datetime import datetime


class ConversionService:
    """
    Service for fetching and caching currency conversion rates.
    Handles caching logic to minimize API calls to exchange rate services.
    """

    def __init__(self):
        self.CONVERT_URL = "https://v6.exchangerate-api.com/v6/{api_key}/pair/{from_currency}/{to_currency}"

    async def get_conversion_rate(
        self,
        db: AsyncSession,
        from_currency: str,
        to_currency: str,
        force_refresh: bool = False,
        allow_expired: bool = False,
    ) -> Dict[str, any]:
        """
        Get conversion rate with caching.

        Args:
            db: Database session
            from_currency: Source currency code
            to_currency: Target currency code
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            Dict with conversion rate and cache info
        """
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        # Same currency, return rate of 1.0
        if from_currency == to_currency:
            now = datetime.utcnow()
            return {
                "from": from_currency,
                "to": to_currency,
                "rate": 1.0,
                "cached": False,
                "fetched_at": now,
                "source": "same_currency",
                "cache_status": {
                    "is_valid": True,
                    "age_minutes": 0,
                    "expires_at": None,
                    "ttl_hours": None,
                },
            }

        # Try to find cached rate (direct or inverse)
        cached_rate = None
        is_inverse = False

        if not force_refresh:
            # Try direct currency pair first
            cached_rate = await self._get_cached_rate(db, from_currency, to_currency)

            # If not found, try inverse pair (e.g., USD->EUR becomes EUR->USD with inverted rate)
            if not cached_rate:
                inverse_cached_rate = await self._get_cached_rate(
                    db, to_currency, from_currency
                )
                if inverse_cached_rate:
                    cached_rate = inverse_cached_rate
                    is_inverse = True

            if cached_rate and (
                cache_management_service.is_conversion_cache_valid(cached_rate)
                or allow_expired
            ):
                # Get cache metadata using the cache management service
                cache_age_minutes = cache_management_service.get_cache_age_minutes(
                    cached_rate
                )
                cache_expires_at = (
                    cache_management_service.get_conversion_cache_expiration(
                        cached_rate
                    )
                )
                is_valid = cache_management_service.is_conversion_cache_valid(
                    cached_rate
                )

                # Calculate the rate (invert if using inverse pair)
                rate = 1.0 / cached_rate.rate if is_inverse else cached_rate.rate

                return {
                    "from": from_currency,
                    "to": to_currency,
                    "rate": rate,
                    "cached": True,
                    "fetched_at": cached_rate.fetched_at,
                    "source": cached_rate.source,
                    "cache_status": {
                        "is_valid": is_valid,
                        "age_minutes": cache_age_minutes,
                        "expires_at": (
                            cache_expires_at.isoformat() if cache_expires_at else None
                        ),
                        "ttl_hours": settings.CONVERSION_CACHE_HOURS,
                        "is_inverse_pair": is_inverse,
                        "using_expired_cache": allow_expired and not is_valid,
                    },
                }

        # Fetch fresh data from exchange rate API
        api_key = getattr(settings, "EXCHANGERATE_API_KEY", None)
        if not api_key:
            raise ValueError("Exchange rate API key not configured")

        url = self.CONVERT_URL.format(
            from_currency=from_currency, to_currency=to_currency, api_key=api_key
        )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)

                if response.status_code != 200:
                    raise ValueError("Failed to fetch conversion rate from API")

                data = response.json()

                if data.get("result") != "success":
                    raise ValueError(
                        f"Conversion API error: {data.get('error-type', 'Unknown error')}"
                    )

                rate = data.get("conversion_rate")
                if rate is None:
                    raise ValueError("No conversion rate in API response")

                # Create a new timestamp for the fetch time
                now = datetime.utcnow()

                # Cache the result
                cached_entry = (
                    await crud_conversion_cache.update_or_create_conversion_cache(
                        db=db,
                        from_currency=from_currency,
                        to_currency=to_currency,
                        rate=rate,
                        source="exchangerate-api",
                    )
                )

                # Calculate cache expiration
                cache_expires_at = (
                    cache_management_service.get_conversion_cache_expiration(
                        cached_entry
                    )
                )

                return {
                    "from": from_currency,
                    "to": to_currency,
                    "rate": rate,
                    "cached": False,
                    "fetched_at": now,
                    "source": "exchangerate-api",
                    "last_update": data.get("time_last_update_utc"),
                    "next_update": data.get("time_next_update_utc"),
                    "cache_status": {
                        "is_valid": True,  # Just created, so it's valid
                        "age_minutes": 0,
                        "expires_at": (
                            cache_expires_at.isoformat() if cache_expires_at else None
                        ),
                        "ttl_hours": settings.CONVERSION_CACHE_HOURS,
                        "is_inverse_pair": False,
                    },
                }

        except httpx.RequestError as e:
            raise ValueError(f"Network error fetching conversion rate: {e}")
        except Exception as e:
            raise ValueError(f"Error fetching conversion rate: {e}")

    async def _get_cached_rate(
        self, db: AsyncSession, from_currency: str, to_currency: str
    ) -> Optional[object]:
        """
        Helper method to get cached conversion rate.

        Args:
            db: Database session
            from_currency: Source currency code
            to_currency: Target currency code

        Returns:
            Cached conversion rate object or None if not found
        """
        return await crud_conversion_cache.get_cached_conversion_rate(
            db=db,
            from_currency=from_currency,
            to_currency=to_currency,
            max_age_hours=999999,  # Get any cached entry regardless of age
        )

    async def convert_amount(
        self,
        db: AsyncSession,
        from_currency: str,
        to_currency: str,
        amount: float,
        force_refresh: bool = False,
        allow_expired: bool = False,
    ) -> Dict[str, any]:
        """
        Convert an amount from one currency to another with caching.

        Args:
            db: Database session
            from_currency: Source currency code
            to_currency: Target currency code
            amount: Amount to convert
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            Dict with converted amount and cache info
        """
        rate_data = await self.get_conversion_rate(
            db=db,
            from_currency=from_currency,
            to_currency=to_currency,
            force_refresh=force_refresh,
            allow_expired=allow_expired,
        )

        converted_amount = amount * rate_data["rate"]

        return {
            "from": rate_data["from"],
            "to": rate_data["to"],
            "amount": amount,
            "converted": converted_amount,
            "rate": rate_data["rate"],
            "cached": rate_data["cached"],
            "fetched_at": rate_data["fetched_at"],
            "source": rate_data["source"],
            "last_update": rate_data.get("last_update"),
            "next_update": rate_data.get("next_update"),
            "cache_status": rate_data.get("cache_status"),
        }


# Global instance
conversion_service = ConversionService()
