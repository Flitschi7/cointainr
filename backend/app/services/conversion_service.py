from sqlalchemy.ext.asyncio import AsyncSession
from app.crud import crud_conversion_cache
from app.core.config import settings
import httpx
from typing import Dict
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
            return {
                "from": from_currency,
                "to": to_currency,
                "rate": 1.0,
                "cached": False,
                "fetched_at": datetime.utcnow(),
                "source": "same_currency",
            }

        # Check cache first (unless force refresh)
        if not force_refresh:
            cached_rate = await crud_conversion_cache.get_cached_conversion_rate(
                db=db,
                from_currency=from_currency,
                to_currency=to_currency,
                max_age_hours=settings.CONVERSION_CACHE_HOURS,
            )
            if cached_rate:
                return {
                    "from": cached_rate.from_currency,
                    "to": cached_rate.to_currency,
                    "rate": cached_rate.rate,
                    "cached": True,
                    "fetched_at": cached_rate.fetched_at,
                    "source": cached_rate.source,
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

                # Cache the result
                await crud_conversion_cache.update_or_create_conversion_cache(
                    db=db,
                    from_currency=from_currency,
                    to_currency=to_currency,
                    rate=rate,
                    source="exchangerate-api",
                )

                return {
                    "from": from_currency,
                    "to": to_currency,
                    "rate": rate,
                    "cached": False,
                    "fetched_at": datetime.utcnow(),
                    "source": "exchangerate-api",
                    "last_update": data.get("time_last_update_utc"),
                    "next_update": data.get("time_next_update_utc"),
                }

        except httpx.RequestError as e:
            raise ValueError(f"Network error fetching conversion rate: {e}")
        except Exception as e:
            raise ValueError(f"Error fetching conversion rate: {e}")

    async def convert_amount(
        self,
        db: AsyncSession,
        from_currency: str,
        to_currency: str,
        amount: float,
        force_refresh: bool = False,
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
        }


# Global instance
conversion_service = ConversionService()
