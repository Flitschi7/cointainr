from sqlalchemy.ext.asyncio import AsyncSession
from app.crud import crud_price_cache
from app.core.config import settings
import finnhub
import yfinance as yf
import httpx
from typing import Dict, Optional
from datetime import datetime


class PriceService:
    """
    Service for fetching and caching asset prices.
    Handles caching logic to minimize API calls.
    """

    def __init__(self):
        # Initialize Finnhub client
        if hasattr(settings, "FINNHUB_API_KEY") and settings.FINNHUB_API_KEY:
            self.finnhub_client = finnhub.Client(api_key=settings.FINNHUB_API_KEY)
        else:
            self.finnhub_client = None

    async def get_stock_price(
        self, db: AsyncSession, identifier: str, force_refresh: bool = False
    ) -> Dict[str, any]:
        """
        Get stock price with caching.

        Args:
            db: Database session
            identifier: Stock symbol or ISIN
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            Dict with symbol, price, currency, and cache info
        """
        # Check cache first (unless force refresh)
        if not force_refresh:
            cached_price = await crud_price_cache.get_cached_price(
                db=db,
                symbol=identifier,
                asset_type="stock",
                max_age_minutes=settings.PRICE_CACHE_MINUTES,
            )
            if cached_price:
                return {
                    "symbol": cached_price.symbol,
                    "price": cached_price.price,
                    "currency": cached_price.currency,
                    "cached": True,
                    "fetched_at": cached_price.fetched_at,
                    "source": cached_price.source,
                }

        # Fetch fresh data
        symbol = identifier
        price = None
        currency = None
        source = None

        # If identifier looks like an ISIN (12 alphanumeric chars), search for symbol
        if len(identifier) == 12 and identifier.isalnum():
            # Try Finnhub first
            if self.finnhub_client:
                try:
                    search_result = self.finnhub_client.symbol_lookup(identifier)
                    if search_result and search_result.get("count", 0) > 0:
                        symbol = search_result["result"][0]["symbol"]
                        quote = self.finnhub_client.quote(symbol)
                        price = quote.get("c")
                        if price is not None and price != 0:
                            currency = "USD"
                            source = "finnhub"
                except Exception as e:
                    print(f"[PriceService] Finnhub error for ISIN {identifier}: {e}")

            # Fallback to Yahoo Finance
            if price is None:
                try:
                    ticker = yf.Ticker(identifier)
                    info = ticker.info
                    price = info.get("regularMarketPrice")
                    currency = info.get("currency", "USD")
                    if price is not None:
                        source = "yfinance"
                        symbol = identifier
                except Exception as e:
                    print(
                        f"[PriceService] Yahoo Finance error for ISIN {identifier}: {e}"
                    )
        else:
            # Regular symbol - try Finnhub first
            if self.finnhub_client:
                try:
                    quote = self.finnhub_client.quote(symbol)
                    price = quote.get("c")
                    if price is not None and price != 0:
                        currency = "USD"
                        source = "finnhub"
                except Exception as e:
                    print(f"[PriceService] Finnhub error for symbol {symbol}: {e}")

            # Fallback to Yahoo Finance
            if price is None:
                try:
                    ticker = yf.Ticker(symbol)
                    info = ticker.info
                    price = info.get("regularMarketPrice")
                    currency = info.get("currency", "USD")
                    if price is not None:
                        source = "yfinance"
                except Exception as e:
                    print(
                        f"[PriceService] Yahoo Finance error for symbol {symbol}: {e}"
                    )

        if price is None:
            raise ValueError(f"Could not fetch price for {identifier}")

        # Cache the result
        await crud_price_cache.update_or_create_price_cache(
            db=db,
            symbol=symbol,
            asset_type="stock",
            price=price,
            currency=currency,
            source=source,
        )

        return {
            "symbol": symbol,
            "price": price,
            "currency": currency,
            "cached": False,
            "fetched_at": datetime.utcnow(),
            "source": source,
        }

    async def get_crypto_price(
        self, db: AsyncSession, symbol: str, force_refresh: bool = False
    ) -> Dict[str, any]:
        """
        Get cryptocurrency price with caching.

        Args:
            db: Database session
            symbol: Crypto symbol (e.g., 'BTC', 'ETH')
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            Dict with symbol, price, currency, and cache info
        """
        # Check cache first (unless force refresh)
        if not force_refresh:
            cached_price = await crud_price_cache.get_cached_price(
                db=db,
                symbol=symbol.upper(),
                asset_type="crypto",
                max_age_minutes=settings.PRICE_CACHE_MINUTES,
            )
            if cached_price:
                return {
                    "symbol": cached_price.symbol,
                    "price": cached_price.price,
                    "currency": cached_price.currency,
                    "cached": True,
                    "fetched_at": cached_price.fetched_at,
                    "source": cached_price.source,
                }

        # Fetch fresh data from CoinGecko
        try:
            async with httpx.AsyncClient() as client:
                # Use CoinGecko API (free tier)
                url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol.lower()}&vs_currencies=usd"
                response = await client.get(url)

                if response.status_code == 200:
                    data = response.json()
                    if symbol.lower() in data and "usd" in data[symbol.lower()]:
                        price = data[symbol.lower()]["usd"]
                        currency = "USD"
                        source = "coingecko"

                        # Cache the result
                        await crud_price_cache.update_or_create_price_cache(
                            db=db,
                            symbol=symbol.upper(),
                            asset_type="crypto",
                            price=price,
                            currency=currency,
                            source=source,
                        )

                        return {
                            "symbol": symbol.upper(),
                            "price": price,
                            "currency": currency,
                            "cached": False,
                            "fetched_at": datetime.utcnow(),
                            "source": source,
                        }
        except Exception as e:
            print(f"[PriceService] CoinGecko error for {symbol}: {e}")

        raise ValueError(f"Could not fetch price for crypto {symbol}")


# Global instance
price_service = PriceService()
