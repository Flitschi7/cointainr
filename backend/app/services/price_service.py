from sqlalchemy.ext.asyncio import AsyncSession
from app.crud import crud_price_cache
from app.core.config import settings
from app.services.cache_management import cache_management_service
import finnhub
import yfinance as yf
import httpx
from typing import Dict, Optional
from datetime import datetime, timedelta


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
        self,
        db: AsyncSession,
        identifier: str,
        force_refresh: bool = False,
        allow_expired: bool = False,
    ) -> Dict[str, any]:
        """
        Get stock price with caching.

        Args:
            db: Database session
            identifier: Stock symbol or ISIN
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            Dict with symbol, price, currency, cache info, and expiration details
        """
        # Check cache first (unless force refresh)
        if not force_refresh:
            # Get any cached entry regardless of age for validation
            cached_price = await crud_price_cache.get_cache_by_symbol(
                db=db, symbol=identifier, asset_type="stock"
            )

            # Use centralized cache validation
            if cached_price and (
                cache_management_service.is_price_cache_valid(cached_price)
                or allow_expired
            ):
                cache_expiration = cache_management_service.get_price_cache_expiration(
                    cached_price
                )
                cache_age = cache_management_service.get_cache_age_minutes(cached_price)
                is_valid = cache_management_service.is_price_cache_valid(cached_price)

                return {
                    "symbol": cached_price.symbol,
                    "price": cached_price.price,
                    "currency": cached_price.currency,
                    "cached": True,
                    "fetched_at": cached_price.fetched_at,
                    "source": cached_price.source,
                    "cache_valid_until": (
                        cache_expiration.isoformat() if cache_expiration else None
                    ),
                    "cache_status": {
                        "is_valid": is_valid,
                        "age_minutes": cache_age,
                        "expires_at": (
                            cache_expiration.isoformat() if cache_expiration else None
                        ),
                        "ttl_minutes": settings.PRICE_CACHE_MINUTES,
                        "using_expired_cache": allow_expired and not is_valid,
                    },
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

        # Handle API failure scenarios with cache fallback
        if price is None:
            # Try to fall back to any cached data (even if expired)
            cached_price = await crud_price_cache.get_cache_by_symbol(
                db=db, symbol=identifier, asset_type="stock"
            )
            if cached_price:
                cache_expiration = cache_management_service.get_price_cache_expiration(
                    cached_price
                )
                cache_age = cache_management_service.get_cache_age_minutes(cached_price)
                return {
                    "symbol": cached_price.symbol,
                    "price": cached_price.price,
                    "currency": cached_price.currency,
                    "cached": True,
                    "fetched_at": cached_price.fetched_at,
                    "source": cached_price.source,
                    "cache_valid_until": (
                        cache_expiration.isoformat() if cache_expiration else None
                    ),
                    "cache_expired": not cache_management_service.is_price_cache_valid(
                        cached_price
                    ),
                    "cache_age_minutes": cache_age,
                    "api_error": True,
                }
            else:
                raise ValueError(
                    f"Could not fetch price for {identifier} and no cached data available"
                )

        # Cache the fresh result
        await crud_price_cache.update_or_create_price_cache(
            db=db,
            symbol=symbol,
            asset_type="stock",
            price=price,
            currency=currency,
            source=source,
        )

        # Calculate cache expiration for fresh data
        now = datetime.utcnow()
        cache_expiration = now + timedelta(minutes=settings.PRICE_CACHE_MINUTES)

        return {
            "symbol": symbol,
            "price": price,
            "currency": currency,
            "cached": False,
            "fetched_at": now,
            "source": source,
            "cache_valid_until": cache_expiration.isoformat(),
            "cache_status": {
                "is_valid": True,  # Just created, so it's valid
                "age_minutes": 0,
                "expires_at": cache_expiration.isoformat(),
                "ttl_minutes": settings.PRICE_CACHE_MINUTES,
                "using_expired_cache": False,
            },
        }

    async def get_crypto_price(
        self,
        db: AsyncSession,
        symbol: str,
        force_refresh: bool = False,
        allow_expired: bool = False,
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
        # Map common crypto symbols to CoinGecko IDs
        symbol_mapping = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "ADA": "cardano",
            "DOT": "polkadot",
            "LINK": "chainlink",
            "LTC": "litecoin",
            "XRP": "ripple",
            "BCH": "bitcoin-cash",
            "BNB": "binancecoin",
            "SOL": "solana",
            "MATIC": "matic-network",
            "AVAX": "avalanche-2",
            "ATOM": "cosmos",
            "ALGO": "algorand",
            "XLM": "stellar",
            "VET": "vechain",
            "ICP": "internet-computer",
            "FIL": "filecoin",
            "TRX": "tron",
            "ETC": "ethereum-classic",
            "THETA": "theta-token",
            "XMR": "monero",
            "EOS": "eos",
            "AAVE": "aave",
            "MKR": "maker",
            "COMP": "compound-governance-token",
            "UNI": "uniswap",
            "SUSHI": "sushi",
            "YFI": "yearn-finance",
            "SNX": "havven",
            "CRV": "curve-dao-token",
            "1INCH": "1inch",
            "BAL": "balancer",
            "ZRX": "0x",
            "REN": "republic-protocol",
            "KNC": "kyber-network-crystal",
            "LRC": "loopring",
            "BAND": "band-protocol",
            "STORJ": "storj",
            "BAT": "basic-attention-token",
            "ZIL": "zilliqa",
            "ENJ": "enjincoin",
            "MANA": "decentraland",
            "SAND": "the-sandbox",
            "GALA": "gala",
            "CHZ": "chiliz",
            "FLOW": "flow",
            "AXS": "axie-infinity",
            "DOGE": "dogecoin",
            "SHIB": "shiba-inu",
        }

        # Get CoinGecko ID for the symbol
        coingecko_id = symbol_mapping.get(symbol.upper(), symbol.lower())

        # Check cache first (unless force refresh)
        if not force_refresh:
            # Get any cached entry regardless of age for validation
            cached_price = await crud_price_cache.get_cache_by_symbol(
                db=db, symbol=symbol.upper(), asset_type="crypto"
            )

            # Use centralized cache validation
            if cached_price and (
                cache_management_service.is_price_cache_valid(cached_price)
                or allow_expired
            ):
                cache_expiration = cache_management_service.get_price_cache_expiration(
                    cached_price
                )
                cache_age = cache_management_service.get_cache_age_minutes(cached_price)
                is_valid = cache_management_service.is_price_cache_valid(cached_price)

                return {
                    "symbol": cached_price.symbol,
                    "price": cached_price.price,
                    "currency": cached_price.currency,
                    "cached": True,
                    "fetched_at": cached_price.fetched_at,
                    "source": cached_price.source,
                    "cache_valid_until": (
                        cache_expiration.isoformat() if cache_expiration else None
                    ),
                    "cache_status": {
                        "is_valid": is_valid,
                        "age_minutes": cache_age,
                        "expires_at": (
                            cache_expiration.isoformat() if cache_expiration else None
                        ),
                        "ttl_minutes": settings.PRICE_CACHE_MINUTES,
                        "using_expired_cache": allow_expired and not is_valid,
                    },
                }

        # Fetch fresh data from CoinGecko
        try:
            async with httpx.AsyncClient() as client:
                # Use CoinGecko API (free tier) with proper ID mapping
                url = f"https://api.coingecko.com/api/v3/simple/price?ids={coingecko_id}&vs_currencies=usd"
                response = await client.get(url)

                if response.status_code == 200:
                    data = response.json()
                    if coingecko_id in data and "usd" in data[coingecko_id]:
                        price = data[coingecko_id]["usd"]
                        currency = "USD"
                        source = "coingecko"

                        # Cache the fresh result
                        await crud_price_cache.update_or_create_price_cache(
                            db=db,
                            symbol=symbol.upper(),
                            asset_type="crypto",
                            price=price,
                            currency=currency,
                            source=source,
                        )

                        # Calculate cache expiration for fresh data
                        now = datetime.utcnow()
                        cache_expiration = now + timedelta(
                            minutes=settings.PRICE_CACHE_MINUTES
                        )

                        return {
                            "symbol": symbol.upper(),
                            "price": price,
                            "currency": currency,
                            "cached": False,
                            "fetched_at": now,
                            "source": source,
                            "cache_valid_until": cache_expiration.isoformat(),
                            "cache_status": {
                                "is_valid": True,  # Just created, so it's valid
                                "age_minutes": 0,
                                "expires_at": cache_expiration.isoformat(),
                                "ttl_minutes": settings.PRICE_CACHE_MINUTES,
                                "using_expired_cache": False,
                            },
                        }
        except Exception as e:
            print(f"[PriceService] CoinGecko error for {symbol}: {e}")

        # Handle API failure scenarios with cache fallback
        # Try to fall back to any cached data (even if expired)
        cached_price = await crud_price_cache.get_cache_by_symbol(
            db=db, symbol=symbol.upper(), asset_type="crypto"
        )
        if cached_price:
            cache_expiration = cache_management_service.get_price_cache_expiration(
                cached_price
            )
            cache_age = cache_management_service.get_cache_age_minutes(cached_price)
            return {
                "symbol": cached_price.symbol,
                "price": cached_price.price,
                "currency": cached_price.currency,
                "cached": True,
                "fetched_at": cached_price.fetched_at,
                "source": cached_price.source,
                "cache_valid_until": (
                    cache_expiration.isoformat() if cache_expiration else None
                ),
                "cache_expired": not cache_management_service.is_price_cache_valid(
                    cached_price
                ),
                "cache_age_minutes": cache_age,
                "api_error": True,
            }
        else:
            raise ValueError(
                f"Could not fetch price for crypto {symbol} and no cached data available"
            )

    async def get_derivative_price(
        self,
        db: AsyncSession,
        isin: str,
        force_refresh: bool = False,
        allow_expired: bool = False,
    ) -> Dict[str, any]:
        """
        Get derivative price using Onvista scraper with caching.

        Args:
            db: Database session
            isin: ISIN of the derivative
            force_refresh: If True, bypass cache and fetch fresh data
            allow_expired: If True, allow expired cache data

        Returns:
            Dict with symbol, price, currency, cache info, and expiration details
        """
        from app.services.onvista_service import onvista_service

        # Check cache first (unless force refresh)
        if not force_refresh:
            # Get any cached entry regardless of age for validation
            cached_price = await crud_price_cache.get_cache_by_symbol(
                db=db, symbol=isin, asset_type="derivative"
            )

            # Use centralized cache validation
            if cached_price and (
                cache_management_service.is_price_cache_valid(cached_price)
                or allow_expired
            ):
                cache_expiration = cache_management_service.get_price_cache_expiration(
                    cached_price
                )
                cache_age = cache_management_service.get_cache_age_minutes(cached_price)
                is_valid = cache_management_service.is_price_cache_valid(cached_price)

                return {
                    "symbol": cached_price.symbol,
                    "price": cached_price.price,
                    "currency": cached_price.currency,
                    "cached": True,
                    "fetched_at": cached_price.fetched_at,
                    "source": cached_price.source,
                    "cache_valid_until": (
                        cache_expiration.isoformat() if cache_expiration else None
                    ),
                    "cache_status": {
                        "is_valid": is_valid,
                        "age_minutes": cache_age,
                        "expires_at": (
                            cache_expiration.isoformat() if cache_expiration else None
                        ),
                        "ttl_minutes": settings.PRICE_CACHE_MINUTES,
                        "using_expired_cache": not is_valid,
                    },
                }

        # Fetch fresh data from Onvista
        try:
            onvista_data = await onvista_service.get_instrument_data(isin)
            if onvista_data:
                price = onvista_data["price"]
                currency = onvista_data["currency"]
                now = datetime.utcnow()

                # Cache the result
                await crud_price_cache.update_or_create_price_cache(
                    db=db,
                    symbol=isin,
                    asset_type="derivative",
                    price=price,
                    currency=currency,
                    source="onvista",
                )

                cache_expiration = now + timedelta(minutes=settings.PRICE_CACHE_MINUTES)

                return {
                    "symbol": isin,
                    "price": price,
                    "currency": currency,
                    "cached": False,
                    "fetched_at": now,
                    "source": "onvista",
                    "cache_valid_until": cache_expiration.isoformat(),
                    "cache_status": {
                        "is_valid": True,  # Just created, so it's valid
                        "age_minutes": 0,
                        "expires_at": cache_expiration.isoformat(),
                        "ttl_minutes": settings.PRICE_CACHE_MINUTES,
                        "using_expired_cache": False,
                    },
                }
        except Exception as e:
            print(f"[PriceService] Onvista error for {isin}: {e}")

        # Handle API failure scenarios with cache fallback
        # Try to fall back to any cached data (even if expired)
        cached_price = await crud_price_cache.get_cache_by_symbol(
            db=db, symbol=isin, asset_type="derivative"
        )
        if cached_price:
            cache_expiration = cache_management_service.get_price_cache_expiration(
                cached_price
            )
            cache_age = cache_management_service.get_cache_age_minutes(cached_price)
            return {
                "symbol": cached_price.symbol,
                "price": cached_price.price,
                "currency": cached_price.currency,
                "cached": True,
                "fetched_at": cached_price.fetched_at,
                "source": cached_price.source,
                "cache_valid_until": (
                    cache_expiration.isoformat() if cache_expiration else None
                ),
                "cache_expired": not cache_management_service.is_price_cache_valid(
                    cached_price
                ),
                "cache_age_minutes": cache_age,
                "api_error": True,
            }
        else:
            raise ValueError(
                f"Could not fetch price for derivative {isin} and no cached data available"
            )


# Global instance
price_service = PriceService()
