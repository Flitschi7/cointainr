from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import finnhub
import yfinance as yf
from app.core.config import settings
from app.db.session import SessionLocal
from app.services.price_service import price_service
from app.services.conversion_service import conversion_service
from app.services.cache_management import cache_management_service
from datetime import datetime, timedelta

router = APIRouter()


# Database dependency
def get_db_dependency():
    """
    Dependency provider for async DB session.
    """

    async def _get_db():
        async with SessionLocal() as session:
            yield session

    return Depends(_get_db)


db_dep = get_db_dependency()

# Finnhub client initialization (for backward compatibility)
if not hasattr(settings, "FINNHUB_API_KEY") or not settings.FINNHUB_API_KEY:
    raise RuntimeError(
        "Finnhub API key not set in environment variable FINNHUB_API_KEY."
    )
finnhub_client = finnhub.Client(api_key=settings.FINNHUB_API_KEY)


@router.get("/stock/{identifier}")
async def get_stock_price(
    identifier: str,
    force_refresh: bool = Query(
        False, description="Force refresh from API, bypass cache"
    ),
    db: AsyncSession = db_dep,
):
    """
    Get the current price for a stock symbol or ISIN with caching.
    Returns cached price if available and fresh (within configured cache TTL).
    Includes cache validity information and expiration details.
    """
    try:
        result = await price_service.get_stock_price(
            db=db, identifier=identifier, force_refresh=force_refresh
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Enhanced error handling for cache-related failures
        error_message = str(e)
        error_code = 502
        error_detail = {
            "message": f"Failed to fetch price: {error_message}",
            "cache_used": False,
            "error_type": "api_error" if "API" in error_message else "unknown_error",
        }

        # Try to fall back to cached data even if expired
        try:
            cached_result = await price_service.get_stock_price(
                db=db, identifier=identifier, force_refresh=False, allow_expired=True
            )
            if cached_result:
                error_detail["cache_fallback_available"] = True
                error_detail["cache_data"] = cached_result
                error_detail["message"] = "API error, using expired cache data"
                return cached_result
        except Exception:
            # If fallback fails, continue with original error
            pass

        raise HTTPException(status_code=error_code, detail=error_detail)


@router.get("/crypto/{symbol}")
async def get_crypto_price(
    symbol: str,
    force_refresh: bool = Query(
        False, description="Force refresh from API, bypass cache"
    ),
    db: AsyncSession = db_dep,
):
    """
    Get the current price for a cryptocurrency symbol with caching.
    Returns cached price if available and fresh (within configured cache TTL).
    Includes cache validity information and expiration details.
    """
    try:
        result = await price_service.get_crypto_price(
            db=db, symbol=symbol, force_refresh=force_refresh
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Enhanced error handling for cache-related failures
        error_message = str(e)
        error_code = 502
        error_detail = {
            "message": f"Failed to fetch price: {error_message}",
            "cache_used": False,
            "error_type": "api_error" if "API" in error_message else "unknown_error",
        }

        # Try to fall back to cached data even if expired
        try:
            cached_result = await price_service.get_crypto_price(
                db=db, symbol=symbol, force_refresh=False, allow_expired=True
            )
            if cached_result:
                error_detail["cache_fallback_available"] = True
                error_detail["cache_data"] = cached_result
                error_detail["message"] = "API error, using expired cache data"
                return cached_result
        except Exception:
            # If fallback fails, continue with original error
            pass

        raise HTTPException(status_code=error_code, detail=error_detail)


@router.get("/convert")
async def convert_currency(
    from_currency: str,
    to_currency: str,
    amount: float = Query(..., description="Amount to convert"),
    force_refresh: bool = Query(
        False, description="Force refresh from API, bypass cache"
    ),
    db: AsyncSession = db_dep,
):
    """
    Convert an amount from one currency to another with caching.
    Returns cached conversion rate if available and fresh (within configured cache TTL).
    Includes cache validity information and expiration details.
    """
    # Validate amount
    if amount is None or not isinstance(amount, (int, float)) or amount <= 0:
        raise HTTPException(status_code=422, detail=f"Invalid amount: {amount}")

    try:
        result = await conversion_service.convert_amount(
            db=db,
            from_currency=from_currency,
            to_currency=to_currency,
            amount=float(amount),
            force_refresh=force_refresh,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Enhanced error handling for cache-related failures
        error_message = str(e)
        error_code = 502
        error_detail = {
            "message": f"Failed to convert currency: {error_message}",
            "cache_used": False,
            "error_type": "api_error" if "API" in error_message else "unknown_error",
        }

        # Try to fall back to cached data even if expired
        try:
            cached_result = await conversion_service.convert_amount(
                db=db,
                from_currency=from_currency,
                to_currency=to_currency,
                amount=float(amount),
                force_refresh=False,
                allow_expired=True,
            )
            if cached_result:
                error_detail["cache_fallback_available"] = True
                error_detail["cache_data"] = cached_result
                error_detail["message"] = "API error, using expired cache data"
                return cached_result
        except Exception:
            # If fallback fails, continue with original error
            pass

        raise HTTPException(status_code=error_code, detail=error_detail)


@router.get("/rate/{from_currency}/{to_currency}")
async def get_conversion_rate(
    from_currency: str,
    to_currency: str,
    force_refresh: bool = Query(
        False, description="Force refresh from API, bypass cache"
    ),
    db: AsyncSession = db_dep,
):
    """
    Get conversion rate between two currencies with caching.
    Returns cached rate if available and fresh (within configured cache TTL).
    Includes cache validity information and expiration details.
    """
    try:
        result = await conversion_service.get_conversion_rate(
            db=db,
            from_currency=from_currency,
            to_currency=to_currency,
            force_refresh=force_refresh,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Enhanced error handling for cache-related failures
        error_message = str(e)
        error_code = 502
        error_detail = {
            "message": f"Failed to fetch conversion rate: {error_message}",
            "cache_used": False,
            "error_type": "api_error" if "API" in error_message else "unknown_error",
        }

        # Try to fall back to cached data even if expired
        try:
            cached_result = await conversion_service.get_conversion_rate(
                db=db,
                from_currency=from_currency,
                to_currency=to_currency,
                force_refresh=False,
                allow_expired=True,
            )
            if cached_result:
                error_detail["cache_fallback_available"] = True
                error_detail["cache_data"] = cached_result
                error_detail["message"] = "API error, using expired cache data"
                return cached_result
        except Exception:
            # If fallback fails, continue with original error
            pass

        raise HTTPException(status_code=error_code, detail=error_detail)


@router.post("/refresh-all")
async def refresh_all_prices(db: AsyncSession = db_dep):
    """
    Refresh prices for all assets in the database.
    Forces fresh API calls for all assets, bypassing cache.
    Includes detailed cache status information in the response.
    """
    from app.crud import crud_asset
    from app.models.asset import AssetType
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select
    from app.models.asset import Asset

    try:
        # Get all assets with explicit loading to avoid lazy loading issues
        stmt = select(Asset)
        result = await db.execute(stmt)
        assets = result.scalars().all()

        # Extract all asset data immediately while in the database session
        asset_data_list = []
        for asset in assets:
            asset_data_list.append(
                {"id": asset.id, "symbol": asset.symbol, "type": asset.type}
            )

        results = []
        errors = []

        # Process each asset using the extracted data
        for asset_data in asset_data_list:
            try:
                asset_id = asset_data["id"]
                asset_symbol = asset_data["symbol"]
                asset_type = asset_data["type"]

                if asset_type == AssetType.STOCK and asset_symbol:
                    result = await price_service.get_stock_price(
                        db=db, identifier=asset_symbol, force_refresh=True
                    )
                    results.append(
                        {
                            "asset_id": asset_id,
                            "symbol": asset_symbol,
                            "type": "stock",
                            "price": result["price"],
                            "currency": result["currency"],
                            "source": result["source"],
                            "cache_status": result.get(
                                "cache_status",
                                {
                                    "is_valid": True,
                                    "age_minutes": 0,
                                    "ttl_minutes": settings.PRICE_CACHE_MINUTES,
                                },
                            ),
                            "cache_valid_until": result.get("cache_valid_until"),
                        }
                    )
                elif asset_type == AssetType.CRYPTO and asset_symbol:
                    result = await price_service.get_crypto_price(
                        db=db, symbol=asset_symbol, force_refresh=True
                    )
                    results.append(
                        {
                            "asset_id": asset_id,
                            "symbol": asset_symbol,
                            "type": "crypto",
                            "price": result["price"],
                            "currency": result["currency"],
                            "source": result["source"],
                            "cache_status": result.get(
                                "cache_status",
                                {
                                    "is_valid": True,
                                    "age_minutes": 0,
                                    "ttl_minutes": settings.PRICE_CACHE_MINUTES,
                                },
                            ),
                            "cache_valid_until": result.get("cache_valid_until"),
                        }
                    )
            except Exception as e:
                # Enhanced error handling with cache fallback attempt
                error_message = str(e)
                error_detail = {
                    "asset_id": asset_data.get("id", "unknown"),
                    "symbol": asset_data.get("symbol", "unknown"),
                    "error": error_message,
                    "error_type": (
                        "api_error" if "API" in error_message else "unknown_error"
                    ),
                }

                # Try to fall back to cached data even if expired
                try:
                    if asset_type == AssetType.STOCK and asset_symbol:
                        cached_result = await price_service.get_stock_price(
                            db=db,
                            identifier=asset_symbol,
                            force_refresh=False,
                            allow_expired=True,
                        )
                        if cached_result:
                            error_detail["cache_fallback_available"] = True
                            error_detail["cache_data"] = {
                                "price": cached_result["price"],
                                "currency": cached_result["currency"],
                                "cached_at": cached_result["fetched_at"],
                                "cache_status": cached_result.get("cache_status"),
                            }
                    elif asset_type == AssetType.CRYPTO and asset_symbol:
                        cached_result = await price_service.get_crypto_price(
                            db=db,
                            symbol=asset_symbol,
                            force_refresh=False,
                            allow_expired=True,
                        )
                        if cached_result:
                            error_detail["cache_fallback_available"] = True
                            error_detail["cache_data"] = {
                                "price": cached_result["price"],
                                "currency": cached_result["currency"],
                                "cached_at": cached_result["fetched_at"],
                                "cache_status": cached_result.get("cache_status"),
                            }
                except Exception:
                    # If fallback fails, continue with original error
                    pass

                errors.append(error_detail)

        return {
            "refreshed": len(results),
            "errors": len(errors),
            "results": results,
            "error_details": errors,
            "timestamp": datetime.utcnow().isoformat(),
            "cache_settings": {
                "price_ttl_minutes": settings.PRICE_CACHE_MINUTES,
                "conversion_ttl_hours": settings.CONVERSION_CACHE_HOURS,
            },
        }

    except Exception as e:
        # Enhanced error handling for database-level errors
        error_message = str(e)
        error_detail = {
            "message": f"Database error: {error_message}",
            "error_type": "database_error",
            "timestamp": datetime.utcnow().isoformat(),
        }
        raise HTTPException(status_code=500, detail=error_detail)


@router.delete("/cache")
async def clear_price_cache(db: AsyncSession = db_dep):
    """
    Clear all cached prices. Next price requests will fetch fresh data from APIs.
    """
    from app.crud import crud_price_cache

    cleared_count = await crud_price_cache.cleanup_old_cache_entries(
        db=db, max_age_days=0
    )
    return {"message": f"Cleared {cleared_count} cached price entries"}


@router.get("/cache/stats")
async def get_cache_stats(db: AsyncSession = db_dep):
    """
    Get statistics about the price cache.
    """
    from sqlalchemy.future import select
    from sqlalchemy import func
    from app.models.price_cache import PriceCache
    from datetime import datetime, timedelta

    # Total cache entries
    total_result = await db.execute(select(func.count(PriceCache.id)))
    total_count = total_result.scalar()

    # Fresh cache entries (within configured minutes)
    cutoff_time = datetime.utcnow() - timedelta(minutes=settings.PRICE_CACHE_MINUTES)
    fresh_result = await db.execute(
        select(func.count(PriceCache.id)).where(PriceCache.fetched_at >= cutoff_time)
    )
    fresh_count = fresh_result.scalar()

    # Cache entries by asset type
    stock_result = await db.execute(
        select(func.count(PriceCache.id)).where(PriceCache.asset_type == "stock")
    )
    stock_count = stock_result.scalar()

    crypto_result = await db.execute(
        select(func.count(PriceCache.id)).where(PriceCache.asset_type == "crypto")
    )
    crypto_count = crypto_result.scalar()

    return {
        "total_entries": total_count,
        "fresh_entries": fresh_count,
        "stock_entries": stock_count,
        "crypto_entries": crypto_count,
        "cache_age_minutes": settings.PRICE_CACHE_MINUTES,
    }


@router.delete("/cache/conversions")
async def clear_conversion_cache(db: AsyncSession = db_dep):
    """
    Clear all cached conversion rates. Next conversion requests will fetch fresh data from APIs.
    """
    from app.crud import crud_conversion_cache

    cleared_count = await crud_conversion_cache.cleanup_old_conversion_cache_entries(
        db=db, max_age_days=0
    )
    return {"message": f"Cleared {cleared_count} cached conversion entries"}


@router.get("/cache/conversions/stats")
async def get_conversion_cache_stats(db: AsyncSession = db_dep):
    """
    Get statistics about the conversion cache.
    """
    from sqlalchemy.future import select
    from sqlalchemy import func
    from app.models.conversion_cache import ConversionCache

    # Total conversion cache entries
    total_result = await db.execute(select(func.count(ConversionCache.id)))
    total_count = total_result.scalar()

    # Fresh conversion cache entries (within configured hours)
    cutoff_time = datetime.utcnow() - timedelta(hours=settings.CONVERSION_CACHE_HOURS)
    fresh_result = await db.execute(
        select(func.count(ConversionCache.id)).where(
            ConversionCache.fetched_at >= cutoff_time
        )
    )
    fresh_count = fresh_result.scalar()

    return {
        "total_entries": total_count,
        "fresh_entries": fresh_count,
        "cache_age_hours": settings.CONVERSION_CACHE_HOURS,
    }


@router.get("/cache/asset-status")
async def get_asset_cache_status(db: AsyncSession = db_dep):
    """
    Get cache status for all assets showing if their cached prices are fresh or stale.
    Includes detailed cache validity information and expiration times.
    """
    from app.crud import crud_asset, crud_price_cache
    from app.models.asset import AssetType
    from datetime import datetime, timedelta

    assets = await crud_asset.get_assets(db=db, skip=0, limit=1000)
    cache_status = []

    for asset in assets:
        # Extract asset data while in async context
        asset_id = asset.id
        asset_symbol = asset.symbol
        asset_type = asset.type

        if asset_type in [AssetType.STOCK, AssetType.CRYPTO] and asset_symbol:
            # Check if we have cached data for this asset
            cache_entry = await crud_price_cache.get_cache_by_symbol(
                db=db, symbol=asset_symbol, asset_type=asset_type.value
            )

            cached_at = None
            expires_at = None
            is_valid = False
            cache_age_minutes = None

            if cache_entry:
                cached_at = cache_entry.fetched_at
                is_valid = cache_management_service.is_price_cache_valid(cache_entry)
                expires_at = cache_management_service.get_price_cache_expiration(
                    cache_entry
                )
                cache_age_minutes = cache_management_service.get_cache_age_minutes(
                    cache_entry
                )

            cache_status.append(
                {
                    "asset_id": asset_id,
                    "symbol": asset_symbol,
                    "type": asset_type.value,
                    "cached_at": cached_at.isoformat() + "Z" if cached_at else None,
                    "cache_ttl_minutes": settings.PRICE_CACHE_MINUTES,
                    "is_valid": is_valid,
                    "expires_at": expires_at.isoformat() + "Z" if expires_at else None,
                    "cache_age_minutes": cache_age_minutes,
                    "needs_refresh": cached_at is None or not is_valid,
                }
            )
        else:
            # Cash assets don't have cache status
            cache_status.append(
                {
                    "asset_id": asset_id,
                    "symbol": asset_symbol,
                    "type": asset_type.value,
                    "cached_at": None,
                    "cache_ttl_minutes": settings.PRICE_CACHE_MINUTES,
                    "is_valid": False,
                    "expires_at": None,
                    "cache_age_minutes": None,
                    "needs_refresh": asset_type
                    != AssetType.CASH,  # Cash doesn't need refresh
                }
            )

    return cache_status
