from fastapi import APIRouter, HTTPException, Query
import finnhub
import yfinance as yf
from app.core.config import settings

router = APIRouter()

# Finnhub client initialization
if not hasattr(settings, "FINNHUB_API_KEY") or not settings.FINNHUB_API_KEY:
    raise RuntimeError(
        "Finnhub API key not set in environment variable FINNHUB_API_KEY."
    )
finnhub_client = finnhub.Client(api_key=settings.FINNHUB_API_KEY)


@router.get("/stock/{identifier}")
async def get_stock_price(identifier: str):
    print(f"[get_stock_price] identifier: {identifier}")
    """
    Get the current price for a stock symbol or ISIN using Finnhub API or Yahoo Finance.
    Always returns the detected currency (e.g., USD, EUR) for correct conversion.
    """
    symbol = identifier
    # If identifier looks like an ISIN (12 alphanumeric chars), search for symbol
    if len(identifier) == 12 and identifier.isalnum():
        try:
            search_result = finnhub_client.symbol_lookup(identifier)
            print(f"[get_stock_price] Finnhub symbol_lookup response: {search_result}")
            if search_result and search_result.get("count", 0) > 0:
                # Use the first matching symbol
                symbol = search_result["result"][0]["symbol"]
                # Try Finnhub price lookup
                try:
                    quote = finnhub_client.quote(symbol)
                    print(f"[get_stock_price] Finnhub response: {quote}")
                    price = quote.get("c")
                    if price is not None and price != 0:
                        currency = "USD"
                        return {"symbol": symbol, "price": price, "currency": currency}
                except Exception as e:
                    print(f"[get_stock_price] Finnhub error: {e}")
            # If Finnhub fails or no price, try Yahoo Finance
            print(f"[get_stock_price] Trying Yahoo Finance for ISIN: {identifier}")
            try:
                ticker = yf.Ticker(identifier)
                info = ticker.info
                print(f"[get_stock_price] Yahoo Finance info: {info}")
                price = info.get("regularMarketPrice")
                currency = info.get("currency", "")
                if price is not None:
                    return {"symbol": identifier, "price": price, "currency": currency}
                else:
                    raise HTTPException(
                        status_code=404,
                        detail="ISIN not found or no price available from Yahoo Finance.",
                    )
            except Exception as e:
                print(f"[get_stock_price] Yahoo Finance error: {e}")
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to fetch price from Yahoo Finance: {e}",
                )
        except Exception as e:
            print(f"[get_stock_price] Finnhub symbol_lookup error: {e}")
            # Try Yahoo Finance directly
            try:
                ticker = yf.Ticker(identifier)
                info = ticker.info
                print(f"[get_stock_price] Yahoo Finance info: {info}")
                price = info.get("regularMarketPrice")
                currency = info.get("currency", "")
                if price is not None:
                    return {"symbol": identifier, "price": price, "currency": currency}
                else:
                    raise HTTPException(
                        status_code=404,
                        detail="ISIN not found or no price available from Yahoo Finance.",
                    )
            except Exception as e2:
                print(f"[get_stock_price] Yahoo Finance error: {e2}")
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to fetch price from Yahoo Finance: {e2}",
                )
    # If not ISIN, use Finnhub symbol lookup
    try:
        quote = finnhub_client.quote(symbol)
        print(f"[get_stock_price] Finnhub response: {quote}")
        price = quote.get("c")  # 'c' is current price
        if price is None or price == 0:
            raise HTTPException(
                status_code=404, detail="Symbol not found or no price available."
            )
        currency = "USD"  # Finnhub returns prices in USD for US stocks
        return {"symbol": symbol, "price": price, "currency": currency}
    except Exception as e:
        print(f"[get_stock_price] Finnhub error: {e}")
        raise HTTPException(
            status_code=502, detail=f"Failed to fetch price from Finnhub: {e}"
        )


# Currency conversion endpoint
CONVERT_URL = "https://v6.exchangerate-api.com/v6/{api_key}/pair/{from_currency}/{to_currency}/{amount}"


@router.get("/convert")
async def convert_currency(
    from_currency: str,
    to_currency: str,
    amount: float = Query(..., description="Amount to convert"),
):
    # Debug logging
    print(
        f"Currency conversion request: from={from_currency}, to={to_currency}, amount={amount} (type: {type(amount)})"
    )
    if amount is None or not isinstance(amount, float) or not (amount > 0):
        raise HTTPException(status_code=422, detail=f"Invalid amount: {amount}")
    """
    Convert an amount from one currency to another using exchangerate-api.com API.
    """
    api_key = getattr(settings, "EXCHANGERATE_API_KEY", None)
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="Exchangerate-api.com API key not set in environment variable EXCHANGERATE_API_KEY.",
        )
    url = CONVERT_URL.format(
        from_currency=from_currency,
        to_currency=to_currency,
        amount=amount,
        api_key=api_key,
    )
    import httpx

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code != 200:
            raise HTTPException(
                status_code=502, detail="Failed to fetch conversion rate."
            )
        data = response.json()
        print(f"[convert_currency] exchangerate-api.com response: {data}")
        try:
            if data.get("result") != "success":
                raise HTTPException(
                    status_code=404,
                    detail=f"Conversion failed: {data.get('error-type', 'Unknown error')}",
                )
            return {
                "from": data["base_code"],
                "to": data["target_code"],
                "amount": amount,
                "converted": data["conversion_result"],
                "rate": data["conversion_rate"],
                "last_update": data.get("time_last_update_utc"),
                "next_update": data.get("time_next_update_utc"),
            }
        except (KeyError, ValueError):
            raise HTTPException(
                status_code=404, detail="Conversion failed or data unavailable."
            )
