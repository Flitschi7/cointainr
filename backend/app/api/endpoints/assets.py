from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.crud import crud_asset
from app.models import asset as asset_model
from app.schemas import asset as asset_schema
from app.db.session import SessionLocal

router = APIRouter()


def get_db_dependency():
    """
    Dependency provider for async DB session.
    Yields an AsyncSession instance.
    """

    async def _get_db():
        async with SessionLocal() as session:
            yield session

    return Depends(_get_db)


db_dep = get_db_dependency()


# --- Asset Endpoints ---


@router.post("/", response_model=asset_schema.AssetRead)
async def create_asset(
    *,
    db: AsyncSession = db_dep,
    asset_in: asset_schema.AssetCreate,
) -> asset_model.Asset:
    """
    Create a new asset. Automatically fetches assetname for ISINs or symbols.
    """
    from app.api.endpoints.price import finnhub_client
    import yfinance as yf
    import httpx

    asset_data = asset_in.model_dump()
    assetname = None
    identifier = asset_data.get("symbol")
    asset_type = asset_data.get("type")

    # Only fetch assetname if symbol/ISIN is provided
    if identifier:
        # Handle crypto assets differently - use CoinGecko
        if asset_type == "crypto":
            try:
                # Map common crypto symbols to CoinGecko IDs (same mapping as in price_service)
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

                coingecko_id = symbol_mapping.get(
                    identifier.upper(), identifier.lower()
                )

                # Fetch crypto info from CoinGecko
                async with httpx.AsyncClient() as client:
                    # Get detailed coin info including name
                    url = f"https://api.coingecko.com/api/v3/coins/{coingecko_id}"
                    response = await client.get(url)

                    if response.status_code == 200:
                        data = response.json()
                        assetname = data.get("name")  # e.g., "Bitcoin", "Ethereum"
                    else:
                        # Fallback: use capitalized symbol
                        assetname = identifier.upper()
            except Exception as e:
                print(f"[Assets] CoinGecko error for {identifier}: {e}")
                # Fallback: use capitalized symbol
                assetname = identifier.upper()

        # Handle stocks/ETFs - use existing logic
        elif asset_type == "stock":
            # ISIN: 12 alphanumeric chars
            if len(identifier) == 12 and identifier.isalnum():
                try:
                    ticker = yf.Ticker(identifier)
                    info = ticker.info
                    assetname = (
                        info.get("shortName")
                        or info.get("longName")
                        or info.get("displayName")
                    )
                except Exception:
                    assetname = None
            else:
                # Try Finnhub symbol lookup
                try:
                    search_result = finnhub_client.symbol_lookup(identifier)
                    if search_result and search_result.get("count", 0) > 0:
                        assetname = search_result["result"][0].get("description")
                except Exception:
                    assetname = None
                # Fallback to Yahoo Finance
                if not assetname:
                    try:
                        ticker = yf.Ticker(identifier)
                        info = ticker.info
                        assetname = (
                            info.get("shortName")
                            or info.get("longName")
                            or info.get("displayName")
                        )
                    except Exception:
                        assetname = None

    asset_data["assetname"] = assetname or identifier or ""
    asset = await crud_asset.create_asset(
        db=db, asset_in=asset_schema.AssetCreate(**asset_data)
    )
    return asset


@router.get("/", response_model=List[asset_schema.AssetRead])
async def read_assets(
    db: AsyncSession = db_dep,
    skip: int = 0,
    limit: int = 100,
) -> List[asset_model.Asset]:
    """
    Retrieve a list of assets.
    Supports pagination via 'skip' and 'limit'.
    """
    assets = await crud_asset.get_assets(db=db, skip=skip, limit=limit)
    return assets


@router.delete("/{asset_id}", response_model=asset_schema.AssetRead)
async def delete_asset(
    *,
    db: AsyncSession = db_dep,
    asset_id: int,
) -> asset_model.Asset:
    """
    Delete an asset by its ID.
    Returns the deleted asset, or raises 404 if not found.
    """
    asset = await crud_asset.delete_asset(db=db, asset_id=asset_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found"
        )
    return asset


@router.put("/{asset_id}", response_model=asset_schema.AssetRead)
async def update_asset(
    *,
    db: AsyncSession = db_dep,
    asset_id: int,
    asset_in: asset_schema.AssetUpdate,
) -> asset_model.Asset:
    """
    Update an asset by its ID.
    Returns the updated asset, or raises 404 if not found.
    """
    asset = await crud_asset.get_asset(db=db, asset_id=asset_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found"
        )
    updated_asset = await crud_asset.update_asset(
        db=db, db_asset=asset, asset_in=asset_in
    )
    return updated_asset
