from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import finnhub
import yfinance as yf
from app.core.config import settings
from app.db.session import SessionLocal
from app.services.price_service import price_service
from app.services.conversion_service import conversion_service
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
    Returns cached price if available and fresh (within 15 minutes).
    """
    try:
        result = await price_service.get_stock_price(
            db=db, identifier=identifier, force_refresh=force_refresh
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch price: {e}")


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
    Returns cached price if available and fresh (within 15 minutes).
    """
    try:
        result = await price_service.get_crypto_price(
            db=db, symbol=symbol, force_refresh=force_refresh
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch price: {e}")


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
    Returns cached conversion rate if available and fresh (within 24 hours by default).
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
        raise HTTPException(status_code=502, detail=f"Failed to convert currency: {e}")


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
    Returns cached rate if available and fresh (within 24 hours by default).
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
        raise HTTPException(
            status_code=502, detail=f"Failed to fetch conversion rate: {e}"
        )


@router.post("/refresh-all")
async def refresh_all_prices(db: AsyncSession = db_dep):
    """
    Refresh prices for all assets in the database.
    Forces fresh API calls for all assets, bypassing cache.
    """
    from app.crud import crud_asset
    from app.models.asset import AssetType

    assets = await crud_asset.get_assets(db=db, skip=0, limit=1000)  # Get all assets
    results = []
    errors = []

    for asset in assets:
        # Extract asset data while in async context to avoid lazy loading issues
        asset_id = asset.id
        asset_symbol = asset.symbol
        asset_type = asset.type

        try:
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
                    }
                )
        except Exception as e:
            errors.append(
                {"asset_id": asset_id, "symbol": asset_symbol, "error": str(e)}
            )

    return {
        "refreshed": len(results),
        "errors": len(errors),
        "results": results,
        "error_details": errors,
    }


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
    """
    from app.crud import crud_asset, crud_price_cache
    from app.models.asset import AssetType
    from datetime import datetime, timedelta

    assets = await crud_asset.get_assets(db=db, skip=0, limit=1000)
    cache_status = []

    # Cache freshness cutoff time
    cutoff_time = datetime.utcnow() - timedelta(minutes=settings.PRICE_CACHE_MINUTES)

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
            if cache_entry:
                cached_at = cache_entry.fetched_at

            cache_status.append(
                {
                    "asset_id": asset_id,
                    "symbol": asset_symbol,
                    "type": asset_type.value,
                    "cached_at": cached_at.isoformat() + "Z" if cached_at else None,
                    "cache_ttl_minutes": settings.PRICE_CACHE_MINUTES,
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
                }
            )

    return cache_status
