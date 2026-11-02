"""
A slow market-data provider must not stall other requests.

Each fake provider blocks its calling thread until released (at most
SLOW_SECONDS). While it blocks, /api/health and the holdings list must answer
within RESPONSIVE_SECONDS. The fakes are released before each test ends, so a
passing run does not wait for the full delay.
"""

import asyncio
import threading
import time
from datetime import datetime, timedelta

import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

import app.api.endpoints.price as price_endpoints
from app.core.config import settings
from app.db.session import engine
from app.models.asset import Asset, AssetType
from app.models.price_cache import PriceCache
from app.services.price_service import price_service

SLOW_SECONDS = 10
RESPONSIVE_SECONDS = 1.0

Session = async_sessionmaker(engine, expire_on_commit=False)


class SlowCall:
    """A provider call that blocks its thread until released."""

    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.entered = threading.Event()
        self.entered_at = None
        self.release = threading.Event()

    def __call__(self, *args, **kwargs):
        self.entered_at = time.monotonic()
        self.entered.set()
        self.release.wait(SLOW_SECONDS)
        if self.error:
            raise self.error
        return self.result


class SlowFinnhub:
    def __init__(self, quote=None, lookup=None):
        self.quote = quote or SlowCall(error=RuntimeError("finnhub down"))
        self.symbol_lookup = lookup or SlowCall(error=RuntimeError("finnhub down"))


@pytest.fixture(autouse=True)
def other_providers_down(monkeypatch):
    def down(*args, **kwargs):
        raise RuntimeError("provider down")

    monkeypatch.setattr("yfinance.Ticker", down)
    monkeypatch.setattr(httpx, "AsyncClient", down)


async def add_holding(**fields):
    async with Session() as session:
        session.add(Asset(**fields))
        await session.commit()


async def wait_until_entered(call: SlowCall):
    deadline = time.monotonic() + SLOW_SECONDS + 5
    while not call.entered.is_set():
        assert time.monotonic() < deadline, "provider was never called"
        await asyncio.sleep(0.01)


async def assert_other_requests_answer(client, call: SlowCall):
    """Health and holdings reads answer while `call` is still blocked."""
    await wait_until_entered(call)

    health = await client.get("/api/health")
    holdings = await client.get("/api/v1/assets/")

    assert health.status_code == 200
    assert holdings.status_code == 200
    assert not call.release.is_set()
    assert time.monotonic() - call.entered_at < RESPONSIVE_SECONDS


async def test_reads_answer_during_slow_forced_refresh(client, monkeypatch):
    quote = SlowCall(result={"c": 190.0})
    monkeypatch.setattr(price_service, "finnhub_client", SlowFinnhub(quote=quote))
    await add_holding(type=AssetType.STOCK, name="Broker", symbol="AAPL", quantity=1)

    refresh = asyncio.create_task(client.post("/api/v1/price/refresh-all"))
    try:
        await assert_other_requests_answer(client, quote)
    finally:
        quote.release.set()
        response = await refresh

    body = response.json()
    assert body["results"][0]["price"] == 190.0


async def test_reads_answer_during_slow_stock_quote(client, monkeypatch):
    quote = SlowCall(result={"c": 55.0})
    monkeypatch.setattr(price_service, "finnhub_client", SlowFinnhub(quote=quote))

    request = asyncio.create_task(
        client.get("/api/v1/price/stock/MSFT", params={"force_refresh": True})
    )
    try:
        await assert_other_requests_answer(client, quote)
    finally:
        quote.release.set()
        response = await request

    assert response.json()["price"] == 55.0


async def test_reads_answer_during_slow_yahoo_fallback(client, monkeypatch):
    class SlowTicker:
        info_call = SlowCall(result={"regularMarketPrice": 120.0, "currency": "EUR"})

        def __init__(self, symbol):
            pass

        @property
        def info(self):
            return self.info_call()

    monkeypatch.setattr(price_service, "finnhub_client", None)
    monkeypatch.setattr("yfinance.Ticker", SlowTicker)

    request = asyncio.create_task(client.get("/api/v1/price/stock/SAP.DE"))
    try:
        await assert_other_requests_answer(client, SlowTicker.info_call)
    finally:
        SlowTicker.info_call.release.set()
        response = await request

    assert response.json()["price"] == 120.0


async def test_reads_answer_during_slow_name_lookup(client, monkeypatch):
    lookup = SlowCall(result={"count": 1, "result": [{"description": "APPLE INC"}]})
    monkeypatch.setattr(
        price_endpoints, "finnhub_client", SlowFinnhub(lookup=lookup)
    )

    create = asyncio.create_task(
        client.post(
            "/api/v1/assets/",
            json={"type": "stock", "name": "Broker", "symbol": "AAPL", "quantity": 1},
        )
    )
    try:
        await assert_other_requests_answer(client, lookup)
    finally:
        lookup.release.set()
        response = await create

    assert response.json()["assetname"] == "APPLE INC"


async def test_stale_quote_is_served_after_slow_failure(client, monkeypatch):
    quote = SlowCall(error=RuntimeError("finnhub timed out"))
    monkeypatch.setattr(price_service, "finnhub_client", SlowFinnhub(quote=quote))
    async with Session() as session:
        session.add(
            PriceCache(
                symbol="AAPL",
                asset_type="stock",
                price=150.0,
                currency="USD",
                source="seed",
                fetched_at=datetime.utcnow()
                - timedelta(minutes=settings.PRICE_CACHE_MINUTES + 5),
            )
        )
        await session.commit()

    request = asyncio.create_task(
        client.get("/api/v1/price/stock/AAPL", params={"force_refresh": True})
    )
    try:
        await assert_other_requests_answer(client, quote)
    finally:
        quote.release.set()
        response = await request

    body = response.json()
    assert body["price"] == 150.0
    assert body["api_error"] is True
