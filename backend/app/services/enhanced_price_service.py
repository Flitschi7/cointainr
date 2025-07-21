"""
Enhanced price service with improved error handling and graceful degradation.

This service extends the original price service with standardized error handling,
detailed logging, and graceful degradation for external API failures.
"""

import logging
import httpx
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.crud import crud_price_cache
from app.core.config import settings
from app.services.cache_management import cache_management_service
from app.services.api_error_handler import with_api_error_handling
from app.utils.graceful_degradation import with_circuit_breaker
from app.core.error_handling import (
    ExternalAPIError,
    DatabaseError,
    NotFoundError,
    CacheError,
)

# Set up logger
logger = logging.getLogger(__name__)


class EnhancedPriceService:
    """
    Enhanced service for fetching and caching asset prices with improved error handling.

    This service provides:
    - Standardized error handling for all API calls
    - Detailed logging for debugging
    - Graceful degradation with cache fallback
    - Consistent response format
    """

    def __init__(self):
        """Initialize the enhanced price service."""
        # Initialize HTTP client for API calls
        self.http_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0))

        # Track API call statistics
        self.api_calls = {
            "finnhub": 0,
            "yahoo": 0,
            "coingecko": 0,
            "errors": 0,
        }

    async def close(self):
        """Close the HTTP client when service is no longer needed."""
        await self.http_client.aclose()

    @with_circuit_breaker(name="finnhub")
    @with_api_error_handling(service_name="Finnhub", operation="get_stock_price")
    async def get_stock_price_from_finnhub(
        self, symbol: str, force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Get stock price from Finnhub API with error handling.

        Args:
            symbol: Stock symbol
            force_refresh: Whether to bypass cache

        Returns:
            Dict with price data

        Raises:
            ExternalAPIError: If API call fails
        """
        start_time = time.time()
        error = False

        try:
            # Check if we have API key
            if not hasattr(settings, "FINNHUB_API_KEY") or not settings.FINNHUB_API_KEY:
                error = True
                raise ExternalAPIError(
                    message="Finnhub API key not configured",
                    status_code=503,
                    details={"symbol": symbol},
                )

            # Make API call
            logger.debug(f"Fetching stock price for {symbol} from Finnhub")
            url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={settings.FINNHUB_API_KEY}"
            response = await self.http_client.get(url)
            response.raise_for_status()

            # Parse response
            data = response.json()

            # Track API call
            self.api_calls["finnhub"] += 1

            # Check if we got valid data
            if "c" not in data or data["c"] == 0:
                error = True
                raise ExternalAPIError(
                    message=f"Invalid price data for {symbol}",
                    status_code=502,
                    details={"symbol": symbol, "response": data},
                )

            # Return formatted response
            return {
                "symbol": symbol,
                "price": data["c"],
                "currency": "USD",  # Finnhub returns prices in USD
                "source": "finnhub",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
        except httpx.HTTPError as e:
            # Track error
            self.api_calls["errors"] += 1
            error = True

            # Raise standardized error
            raise ExternalAPIError(
                message=f"Finnhub API error for {symbol}: {str(e)}",
                status_code=502,
                details={"symbol": symbol, "error_type": type(e).__name__},
                original_error=e,
            )
        finally:
            # Track in performance monitoring
            execution_time_ms = (time.time() - start_time) * 1000
            try:
                from app.core.performance_monitoring import record_external_api_call

                record_external_api_call("finnhub", execution_time_ms, error)
            except ImportError:
                pass

    @with_circuit_breaker(name="yahoo_finance")
    @with_api_error_handling(service_name="Yahoo Finance", operation="get_stock_price")
    async def get_stock_price_from_yahoo(
        self, symbol: str, force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Get stock price from Yahoo Finance API with error handling.

        Args:
            symbol: Stock symbol
            force_refresh: Whether to bypass cache

        Returns:
            Dict with price data

        Raises:
            ExternalAPIError: If API call fails
        """
        start_time = time.time()
        error = False

        try:
            # Make API call
            logger.debug(f"Fetching stock price for {symbol} from Yahoo Finance")

            # yfinance is synchronous, so we need to run it in a thread
            import yfinance as yf
            import asyncio
            from concurrent.futures import ThreadPoolExecutor

            # Create a function to run in a thread
            def get_yahoo_data(sym):
                try:
                    ticker = yf.Ticker(sym)
                    data = ticker.info
                    return data
                except Exception as e:
                    raise ExternalAPIError(
                        message=f"Yahoo Finance API error for {sym}: {str(e)}",
                        status_code=502,
                        details={"symbol": sym, "error_type": type(e).__name__},
                        original_error=e,
                    )

            # Run in a thread
            with ThreadPoolExecutor() as executor:
                data = await asyncio.get_event_loop().run_in_executor(
                    executor, get_yahoo_data, symbol
                )

            # Track API call
            self.api_calls["yahoo"] += 1

            # Check if we got valid data
            if (
                not data
                or "regularMarketPrice" not in data
                or not data["regularMarketPrice"]
            ):
                error = True
                raise ExternalAPIError(
                    message=f"Invalid price data for {symbol}",
                    status_code=502,
                    details={"symbol": symbol},
                )

            # Get currency from data or default to USD
            currency = data.get("currency", "USD")

            # Return formatted response
            return {
                "symbol": symbol,
                "price": data["regularMarketPrice"],
                "currency": currency,
                "source": "yahoo",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            # Track error
            self.api_calls["errors"] += 1
            error = True

            # If not already an ExternalAPIError, wrap it
            if not isinstance(e, ExternalAPIError):
                raise ExternalAPIError(
                    message=f"Yahoo Finance API error for {symbol}: {str(e)}",
                    status_code=502,
                    details={"symbol": symbol, "error_type": type(e).__name__},
                    original_error=e,
                )
            raise
        finally:
            # Track in performance monitoring
            execution_time_ms = (time.time() - start_time) * 1000
            try:
                from app.core.performance_monitoring import record_external_api_call

                record_external_api_call("yahoo_finance", execution_time_ms, error)
            except ImportError:
                pass

    @with_circuit_breaker(name="coingecko")
    @with_api_error_handling(service_name="CoinGecko", operation="get_crypto_price")
    async def get_crypto_price_from_coingecko(
        self, symbol: str, force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Get cryptocurrency price from CoinGecko API with error handling.

        Args:
            symbol: Cryptocurrency symbol
            force_refresh: Whether to bypass cache

        Returns:
            Dict with price data

        Raises:
            ExternalAPIError: If API call fails
        """
        start_time = time.time()
        error = False

        try:
            # Make API call
            logger.debug(f"Fetching crypto price for {symbol} from CoinGecko")

            # CoinGecko expects lowercase symbols
            symbol_lower = symbol.lower()

            # Make API call
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol_lower}&vs_currencies=usd"
            response = await self.http_client.get(url)
            response.raise_for_status()

            # Parse response
            data = response.json()

            # Track API call
            self.api_calls["coingecko"] += 1

            # Check if we got valid data
            if not data or symbol_lower not in data or "usd" not in data[symbol_lower]:
                error = True
                raise ExternalAPIError(
                    message=f"Invalid price data for {symbol}",
                    status_code=502,
                    details={"symbol": symbol, "response": data},
                )

            # Return formatted response
            return {
                "symbol": symbol,
                "price": data[symbol_lower]["usd"],
                "currency": "USD",  # CoinGecko returns prices in USD
                "source": "coingecko",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
        except httpx.HTTPError as e:
            # Track error
            self.api_calls["errors"] += 1
            error = True

            # Raise standardized error
            raise ExternalAPIError(
                message=f"CoinGecko API error for {symbol}: {str(e)}",
                status_code=502,
                details={"symbol": symbol, "error_type": type(e).__name__},
                original_error=e,
            )
        finally:
            # Track in performance monitoring
            execution_time_ms = (time.time() - start_time) * 1000
            try:
                from app.core.performance_monitoring import record_external_api_call

                record_external_api_call("coingecko", execution_time_ms, error)
            except ImportError:
                pass

    async def get_stock_price(
        self,
        db: AsyncSession,
        identifier: str,
        force_refresh: bool = False,
        allow_expired: bool = False,
    ) -> Dict[str, Any]:
        """
        Get stock price with caching and error handling.

        Args:
            db: Database session
            identifier: Stock symbol or ISIN
            force_refresh: If True, bypass cache and fetch fresh data
            allow_expired: If True, allow using expired cache entries

        Returns:
            Dict with symbol, price, currency, cache info, and expiration details

        Raises:
            NotFoundError: If stock symbol is not found
            DatabaseError: If database operation fails
            ExternalAPIError: If API call fails and no cache fallback is available
        """
        try:
            # Check cache first (unless force refresh)
            if not force_refresh:
                try:
                    # Get any cached entry regardless of age for validation
                    cached_price = await crud_price_cache.get_cache_by_symbol(
                        db=db, symbol=identifier, asset_type="stock"
                    )

                    # Use centralized cache validation
                    is_valid = cache_management_service.is_price_cache_valid(
                        cached_price
                    )

                    # If cache is valid or we allow expired entries and have one
                    if is_valid or (allow_expired and cached_price):
                        # Get cache status for response
                        cache_status = cache_management_service.get_cache_status(
                            cached_price, settings.PRICE_CACHE_MINUTES, force_refresh
                        )

                        # Get cache expiration
                        cache_expiration = (
                            cache_management_service.get_price_cache_expiration(
                                cached_price
                            )
                        )

                        # Return cached data with cache status
                        return {
                            "symbol": cached_price.symbol,
                            "price": cached_price.price,
                            "currency": cached_price.currency,
                            "cached": True,
                            "source": cached_price.source,
                            "fetched_at": cached_price.fetched_at.isoformat(),
                            "cache_status": cache_status,
                            "cache_valid_until": (
                                cache_expiration.isoformat()
                                if cache_expiration
                                else None
                            ),
                        }
                except SQLAlchemyError as e:
                    # Log database error but continue to fetch fresh data
                    logger.error(f"Database error when fetching cached price: {str(e)}")

            # No valid cache or force refresh, fetch from API
            # Try Finnhub first, then fall back to Yahoo Finance
            try:
                price_data = await self.get_stock_price_from_finnhub(
                    identifier, force_refresh
                )
            except ExternalAPIError:
                # Fall back to Yahoo Finance
                price_data = await self.get_stock_price_from_yahoo(
                    identifier, force_refresh
                )

            # Store in cache
            try:
                await crud_price_cache.create_or_update_price_cache(
                    db=db,
                    symbol=identifier,
                    asset_type="stock",
                    price=price_data["price"],
                    currency=price_data["currency"],
                    source=price_data["source"],
                )
                await db.commit()
            except SQLAlchemyError as e:
                # Log database error but continue with response
                logger.error(f"Database error when storing price in cache: {str(e)}")
                await db.rollback()

            # Get cache status for response
            cache_status = {
                "is_valid": True,
                "cached_at": price_data["fetched_at"],
                "expires_at": (
                    datetime.fromisoformat(price_data["fetched_at"])
                    + timedelta(minutes=settings.PRICE_CACHE_MINUTES)
                ).isoformat(),
                "cache_age_minutes": 0,
                "ttl_minutes": settings.PRICE_CACHE_MINUTES,
                "force_refresh_requested": force_refresh,
            }

            # Return fresh data with cache status
            return {
                "symbol": identifier,
                "price": price_data["price"],
                "currency": price_data["currency"],
                "cached": False,
                "source": price_data["source"],
                "fetched_at": price_data["fetched_at"],
                "cache_status": cache_status,
                "cache_valid_until": cache_status["expires_at"],
            }
        except NotFoundError:
            # Re-raise not found errors
            raise
        except DatabaseError:
            # Re-raise database errors
            raise
        except ExternalAPIError:
            # Re-raise external API errors (these should be handled by the decorator)
            raise
        except Exception as e:
            # Catch any other exceptions and wrap them
            logger.error(
                f"Unexpected error in get_stock_price: {str(e)}", exc_info=True
            )
            raise ExternalAPIError(
                message=f"Failed to get stock price for {identifier}: {str(e)}",
                status_code=500,
                details={"symbol": identifier, "error_type": type(e).__name__},
                original_error=e,
            )

    async def get_crypto_price(
        self,
        db: AsyncSession,
        symbol: str,
        force_refresh: bool = False,
        allow_expired: bool = False,
    ) -> Dict[str, Any]:
        """
        Get cryptocurrency price with caching and error handling.

        Args:
            db: Database session
            symbol: Cryptocurrency symbol
            force_refresh: If True, bypass cache and fetch fresh data
            allow_expired: If True, allow using expired cache entries

        Returns:
            Dict with symbol, price, currency, cache info, and expiration details

        Raises:
            NotFoundError: If crypto symbol is not found
            DatabaseError: If database operation fails
            ExternalAPIError: If API call fails and no cache fallback is available
        """
        try:
            # Check cache first (unless force refresh)
            if not force_refresh:
                try:
                    # Get any cached entry regardless of age for validation
                    cached_price = await crud_price_cache.get_cache_by_symbol(
                        db=db, symbol=symbol, asset_type="crypto"
                    )

                    # Use centralized cache validation
                    is_valid = cache_management_service.is_price_cache_valid(
                        cached_price
                    )

                    # If cache is valid or we allow expired entries and have one
                    if is_valid or (allow_expired and cached_price):
                        # Get cache status for response
                        cache_status = cache_management_service.get_cache_status(
                            cached_price, settings.PRICE_CACHE_MINUTES, force_refresh
                        )

                        # Get cache expiration
                        cache_expiration = (
                            cache_management_service.get_price_cache_expiration(
                                cached_price
                            )
                        )

                        # Return cached data with cache status
                        return {
                            "symbol": cached_price.symbol,
                            "price": cached_price.price,
                            "currency": cached_price.currency,
                            "cached": True,
                            "source": cached_price.source,
                            "fetched_at": cached_price.fetched_at.isoformat(),
                            "cache_status": cache_status,
                            "cache_valid_until": (
                                cache_expiration.isoformat()
                                if cache_expiration
                                else None
                            ),
                        }
                except SQLAlchemyError as e:
                    # Log database error but continue to fetch fresh data
                    logger.error(f"Database error when fetching cached price: {str(e)}")

            # No valid cache or force refresh, fetch from API
            price_data = await self.get_crypto_price_from_coingecko(
                symbol, force_refresh
            )

            # Store in cache
            try:
                await crud_price_cache.create_or_update_price_cache(
                    db=db,
                    symbol=symbol,
                    asset_type="crypto",
                    price=price_data["price"],
                    currency=price_data["currency"],
                    source=price_data["source"],
                )
                await db.commit()
            except SQLAlchemyError as e:
                # Log database error but continue with response
                logger.error(f"Database error when storing price in cache: {str(e)}")
                await db.rollback()

            # Get cache status for response
            cache_status = {
                "is_valid": True,
                "cached_at": price_data["fetched_at"],
                "expires_at": (
                    datetime.fromisoformat(price_data["fetched_at"])
                    + timedelta(minutes=settings.PRICE_CACHE_MINUTES)
                ).isoformat(),
                "cache_age_minutes": 0,
                "ttl_minutes": settings.PRICE_CACHE_MINUTES,
                "force_refresh_requested": force_refresh,
            }

            # Return fresh data with cache status
            return {
                "symbol": symbol,
                "price": price_data["price"],
                "currency": price_data["currency"],
                "cached": False,
                "source": price_data["source"],
                "fetched_at": price_data["fetched_at"],
                "cache_status": cache_status,
                "cache_valid_until": cache_status["expires_at"],
            }
        except NotFoundError:
            # Re-raise not found errors
            raise
        except DatabaseError:
            # Re-raise database errors
            raise
        except ExternalAPIError:
            # Re-raise external API errors (these should be handled by the decorator)
            raise
        except Exception as e:
            # Catch any other exceptions and wrap them
            logger.error(
                f"Unexpected error in get_crypto_price: {str(e)}", exc_info=True
            )
            raise ExternalAPIError(
                message=f"Failed to get crypto price for {symbol}: {str(e)}",
                status_code=500,
                details={"symbol": symbol, "error_type": type(e).__name__},
                original_error=e,
            )

    async def get_api_stats(self) -> Dict[str, Any]:
        """
        Get statistics about API calls made by this service.

        Returns:
            Dict with API call statistics
        """
        return {
            "api_calls": self.api_calls,
            "total_calls": sum(self.api_calls.values()),
            "error_rate": (
                self.api_calls["errors"]
                / max(1, sum(self.api_calls.values()) - self.api_calls["errors"])
            )
            * 100,
        }


# Create a singleton instance
enhanced_price_service = EnhancedPriceService()
