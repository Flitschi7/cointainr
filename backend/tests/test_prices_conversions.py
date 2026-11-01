"""
Quotes and conversion rates through the HTTP API, pinned to current behavior.

Every provider (Finnhub, Yahoo, CoinGecko, Onvista, exchangerate-api) is a
fake. Cache age is set by writing cache rows with an old `fetched_at`.
"""

from datetime import datetime, timedelta

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import settings
from app.db.session import engine
from app.models.conversion_cache import ConversionCache
from app.models.price_cache import PriceCache
from app.services.onvista_service import onvista_service
from app.services.price_service import price_service

PRICE = "/api/v1/price"
STALE = timedelta(minutes=settings.PRICE_CACHE_MINUTES + 5)
STALE_RATE = timedelta(hours=settings.CONVERSION_CACHE_HOURS + 1)

Session = async_sessionmaker(engine, expire_on_commit=False)


class FakeFinnhub:
    def __init__(self, quotes=None, lookups=None):
        self.quotes = quotes or {}
        self.lookups = lookups or {}
        self.calls = []

    def quote(self, symbol):
        self.calls.append(("quote", symbol))
        if symbol not in self.quotes:
            raise RuntimeError("finnhub down")
        return {"c": self.quotes[symbol]}

    def symbol_lookup(self, query):
        self.calls.append(("lookup", query))
        if query not in self.lookups:
            raise RuntimeError("finnhub down")
        return {"count": 1, "result": [{"symbol": self.lookups[query]}]}


class FakeTicker:
    info_by_symbol: dict[str, dict] = {}

    def __init__(self, symbol):
        if symbol not in self.info_by_symbol:
            raise RuntimeError("yahoo down")
        self.info = self.info_by_symbol[symbol]


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class FakeHttp:
    """Stands in for httpx.AsyncClient; answers by URL prefix."""

    def __init__(self):
        self.routes: dict[str, tuple[int, dict]] = {}
        self.calls: list[str] = []

    def client(self):
        fake = self

        class Client:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def get(self, url):
                fake.calls.append(url)
                for prefix, (status, payload) in fake.routes.items():
                    if url.startswith(prefix):
                        return FakeResponse(status, payload)
                raise httpx.ConnectError("provider down")

        return Client


@pytest.fixture
def finnhub(monkeypatch):
    fake = FakeFinnhub()
    monkeypatch.setattr(price_service, "finnhub_client", fake)
    return fake


@pytest.fixture
def yahoo(monkeypatch):
    FakeTicker.info_by_symbol = {}
    monkeypatch.setattr("yfinance.Ticker", FakeTicker)
    return FakeTicker.info_by_symbol


@pytest.fixture
def http(monkeypatch):
    fake = FakeHttp()
    monkeypatch.setattr(httpx, "AsyncClient", fake.client())
    return fake


@pytest.fixture
def onvista(monkeypatch):
    data: dict[str, dict] = {}

    async def get_instrument_data(isin):
        if isin not in data:
            raise RuntimeError("onvista down")
        return data[isin]

    monkeypatch.setattr(onvista_service, "get_instrument_data", get_instrument_data)
    return data


@pytest.fixture(autouse=True)
def all_providers_faked(finnhub, yahoo, http, onvista):
    """Each test starts with every provider down."""


async def cache_price(symbol, asset_type, price, currency="USD", age=timedelta(0)):
    async with Session() as session:
        session.add(
            PriceCache(
                symbol=symbol,
                asset_type=asset_type,
                price=price,
                currency=currency,
                source="seed",
                fetched_at=datetime.utcnow() - age,
            )
        )
        await session.commit()


async def cache_rate(from_currency, to_currency, rate, age=timedelta(0)):
    async with Session() as session:
        session.add(
            ConversionCache(
                from_currency=from_currency,
                to_currency=to_currency,
                rate=rate,
                source="seed",
                fetched_at=datetime.utcnow() - age,
            )
        )
        await session.commit()


async def count(model):
    async with Session() as session:
        return (await session.execute(select(func.count()).select_from(model))).scalar()


# --- Stocks ---


async def test_stock_quote_comes_from_finnhub_and_is_cached(client, finnhub):
    finnhub.quotes = {"AAPL": 190.5}

    first = (await client.get(f"{PRICE}/stock/AAPL")).json()
    second = (await client.get(f"{PRICE}/stock/AAPL")).json()

    assert first["price"] == 190.5
    assert first["currency"] == "USD"
    assert first["source"] == "finnhub"
    assert first["cached"] is False
    assert second["price"] == 190.5
    assert second["cached"] is True
    assert finnhub.calls == [("quote", "AAPL")]


async def test_stock_quote_falls_back_to_yahoo(client, yahoo):
    yahoo["SAP.DE"] = {"regularMarketPrice": 120.0, "currency": "EUR"}

    body = (await client.get(f"{PRICE}/stock/SAP.DE")).json()

    assert (body["price"], body["currency"], body["source"]) == (
        120.0,
        "EUR",
        "yfinance",
    )


async def test_stock_quote_of_zero_from_finnhub_skips_yahoo(client, finnhub, yahoo):
    """Current behavior: a 0 quote is not None, so Yahoo is never tried; the
    cache schema then rejects the missing currency (a ValueError, so 404)."""
    finnhub.quotes = {"ZERO": 0}
    yahoo["ZERO"] = {"regularMarketPrice": 5.0, "currency": "USD"}

    response = await client.get(f"{PRICE}/stock/ZERO")

    assert response.status_code == 404
    assert await count(PriceCache) == 0


async def test_stock_isin_resolves_symbol_but_caches_under_symbol(client, finnhub):
    """Current behavior: the quote is cached under the resolved symbol, so a
    repeated ISIN request misses the cache and calls Finnhub again."""
    finnhub.lookups = {"US0378331005": "AAPL"}
    finnhub.quotes = {"AAPL": 190.0}

    first = (await client.get(f"{PRICE}/stock/US0378331005")).json()
    second = (await client.get(f"{PRICE}/stock/US0378331005")).json()

    assert first["symbol"] == "AAPL"
    assert second["cached"] is False
    assert finnhub.calls.count(("quote", "AAPL")) == 2


async def test_fresh_stock_cache_is_used_without_provider_calls(client, finnhub):
    await cache_price("AAPL", "stock", 180.0)

    body = (await client.get(f"{PRICE}/stock/AAPL")).json()

    assert body["price"] == 180.0
    assert body["cached"] is True
    assert body["cache_status"]["is_valid"] is True
    assert finnhub.calls == []


async def test_force_refresh_bypasses_fresh_stock_cache(client, finnhub):
    await cache_price("AAPL", "stock", 180.0)
    finnhub.quotes = {"AAPL": 191.0}

    body = (
        await client.get(f"{PRICE}/stock/AAPL", params={"force_refresh": True})
    ).json()

    assert body["price"] == 191.0
    assert body["cached"] is False


async def test_expired_stock_cache_is_refreshed(client, finnhub):
    await cache_price("AAPL", "stock", 150.0, age=STALE)
    finnhub.quotes = {"AAPL": 191.0}

    body = (await client.get(f"{PRICE}/stock/AAPL")).json()

    assert body["price"] == 191.0
    assert body["cached"] is False


async def test_stale_stock_quote_is_served_when_providers_fail(client):
    await cache_price("AAPL", "stock", 150.0, age=STALE)

    response = await client.get(f"{PRICE}/stock/AAPL")

    assert response.status_code == 200
    body = response.json()
    assert body["price"] == 150.0
    assert body["cached"] is True
    assert body["api_error"] is True
    assert body["cache_expired"] is True


async def test_stale_stock_quote_is_served_on_forced_refresh_failure(client):
    await cache_price("AAPL", "stock", 150.0, age=STALE)

    response = await client.get(f"{PRICE}/stock/AAPL", params={"force_refresh": True})

    assert response.status_code == 200
    assert response.json()["price"] == 150.0
    assert response.json()["api_error"] is True


async def test_stock_without_quote_or_cache_is_404(client):
    response = await client.get(f"{PRICE}/stock/NOPE")

    assert response.status_code == 404


# --- Crypto ---


async def test_crypto_quote_comes_from_coingecko_by_mapped_id(client, http):
    http.routes = {
        "https://api.coingecko.com/api/v3/simple/price": (
            200,
            {"bitcoin": {"usd": 65000.0}},
        )
    }

    first = (await client.get(f"{PRICE}/crypto/btc")).json()
    second = (await client.get(f"{PRICE}/crypto/BTC")).json()

    assert http.calls == [
        "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    ]
    assert (first["symbol"], first["price"], first["currency"]) == (
        "BTC",
        65000.0,
        "USD",
    )
    assert first["source"] == "coingecko"
    assert second["cached"] is True


async def test_unmapped_crypto_uses_lowercase_symbol_as_id(client, http):
    http.routes = {
        "https://api.coingecko.com/": (200, {"pepe": {"usd": 0.0000123}}),
    }

    body = (await client.get(f"{PRICE}/crypto/PEPE")).json()

    assert "ids=pepe&" in http.calls[0]
    assert body["price"] == 0.0000123


async def test_stale_crypto_quote_is_served_when_coingecko_fails(client):
    await cache_price("ETH", "crypto", 3000.0, age=STALE)

    body = (await client.get(f"{PRICE}/crypto/eth")).json()

    assert body["price"] == 3000.0
    assert body["api_error"] is True
    assert body["cache_expired"] is True


async def test_crypto_without_quote_or_cache_is_404(client, http):
    http.routes = {"https://api.coingecko.com/": (200, {})}

    response = await client.get(f"{PRICE}/crypto/NOPE")

    assert response.status_code == 404


# --- Derivatives ---


async def test_derivative_quote_comes_from_onvista(client, onvista):
    onvista["DE000XX00000"] = {"price": 1.23, "currency": "EUR", "name": "Turbo"}

    body = (await client.get(f"{PRICE}/derivative/DE000XX00000")).json()

    assert (body["price"], body["currency"], body["source"]) == (1.23, "EUR", "onvista")


async def test_stale_derivative_quote_is_served_when_onvista_fails(client):
    await cache_price("DE000XX00000", "derivative", 1.1, "EUR", age=STALE)

    body = (await client.get(f"{PRICE}/derivative/DE000XX00000")).json()

    assert body["price"] == 1.1
    assert body["api_error"] is True


async def test_derivative_without_quote_or_cache_is_404(client):
    response = await client.get(f"{PRICE}/derivative/DE000XX00000")

    assert response.status_code == 404


# --- Conversion rates ---

RATE_API = "https://v6.exchangerate-api.com/v6/"


def rate_reply(rate):
    return (200, {"result": "success", "conversion_rate": rate})


async def test_same_currency_rate_is_one_without_provider_call(client, http):
    body = (await client.get(f"{PRICE}/rate/eur/EUR")).json()

    assert body["rate"] == 1.0
    assert body["source"] == "same_currency"
    assert http.calls == []


async def test_rate_comes_from_exchangerate_api_and_is_cached(client, http):
    http.routes = {RATE_API: rate_reply(0.92)}

    first = (await client.get(f"{PRICE}/rate/usd/eur")).json()
    second = (await client.get(f"{PRICE}/rate/USD/EUR")).json()

    assert http.calls == [f"{RATE_API}test-placeholder/pair/USD/EUR"]
    assert (first["from"], first["to"], first["rate"]) == ("USD", "EUR", 0.92)
    assert first["cached"] is False
    assert second["cached"] is True
    assert second["rate"] == 0.92


async def test_cached_inverse_pair_is_inverted(client, http):
    await cache_rate("EUR", "USD", 1.25)

    body = (await client.get(f"{PRICE}/rate/USD/EUR")).json()

    assert body["rate"] == pytest.approx(0.8)
    assert body["cache_status"]["is_inverse_pair"] is True
    assert http.calls == []


async def test_expired_rate_is_refreshed(client, http):
    await cache_rate("USD", "EUR", 0.5, age=STALE_RATE)
    http.routes = {RATE_API: rate_reply(0.92)}

    body = (await client.get(f"{PRICE}/rate/USD/EUR")).json()

    assert body["rate"] == 0.92
    assert body["cached"] is False


async def test_expired_rate_is_not_served_when_api_fails(client):
    """Current behavior: the service raises ValueError on API failure and the
    endpoint maps it to 404 before its expired-cache fallback runs."""
    await cache_rate("USD", "EUR", 0.9, age=STALE_RATE)

    response = await client.get(f"{PRICE}/rate/USD/EUR")

    assert response.status_code == 404


@pytest.mark.parametrize(
    "reply",
    [
        (500, {}),
        (200, {"result": "error", "error-type": "invalid-key"}),
        (200, {"result": "success"}),
    ],
    ids=["http-error", "api-error", "no-rate"],
)
async def test_rate_api_failures_without_cache_are_404(client, http, reply):
    http.routes = {RATE_API: reply}

    response = await client.get(f"{PRICE}/rate/USD/EUR")

    assert response.status_code == 404
    assert await count(ConversionCache) == 0


async def test_convert_multiplies_amount_by_rate(client):
    await cache_rate("USD", "EUR", 0.9)

    body = (
        await client.get(
            f"{PRICE}/convert",
            params={"from_currency": "USD", "to_currency": "EUR", "amount": 200},
        )
    ).json()

    assert body["amount"] == 200
    assert body["converted"] == pytest.approx(180.0)
    assert body["rate"] == 0.9


@pytest.mark.parametrize("amount", [0, -5])
async def test_convert_rejects_non_positive_amount(client, amount):
    response = await client.get(
        f"{PRICE}/convert",
        params={"from_currency": "USD", "to_currency": "EUR", "amount": amount},
    )

    assert response.status_code == 422


# --- Refresh all ---


async def test_refresh_all_forces_quotes_for_priced_holdings(
    client, finnhub, http, onvista
):
    for fields in [
        {"type": "cash", "name": "Bank", "quantity": 100},
        {"type": "stock", "name": "Broker", "symbol": "AAPL", "quantity": 1},
        {"type": "crypto", "name": "Wallet", "symbol": "BTC", "quantity": 1},
        {
            "type": "derivative",
            "name": "Broker",
            "symbol": "DE000XX00000",
            "quantity": 1,
        },
    ]:
        assert (await client.post("/api/v1/assets/", json=fields)).status_code == 200
    await cache_price("AAPL", "stock", 100.0)
    finnhub.quotes = {"AAPL": 190.0}
    http.routes = {"https://api.coingecko.com/": (200, {"bitcoin": {"usd": 65000.0}})}
    onvista["DE000XX00000"] = {"price": 1.5, "currency": "EUR"}

    body = (await client.post(f"{PRICE}/refresh-all")).json()

    assert body["refreshed"] == 3
    assert body["errors"] == 0
    prices = {r["symbol"]: (r["type"], r["price"]) for r in body["results"]}
    assert prices == {
        "AAPL": ("stock", 190.0),
        "BTC": ("crypto", 65000.0),
        "DE000XX00000": ("derivative", 1.5),
    }


async def test_refresh_all_reports_stale_fallback_when_provider_fails(client):
    await client.post(
        "/api/v1/assets/",
        json={"type": "crypto", "name": "Wallet", "symbol": "ETH", "quantity": 1},
    )
    await cache_price("ETH", "crypto", 3000.0, age=STALE)

    body = (await client.post(f"{PRICE}/refresh-all")).json()

    assert body["refreshed"] == 1
    assert body["results"][0]["price"] == 3000.0
    assert body["errors"] == 0


async def test_refresh_all_reports_error_without_cache(client):
    await client.post(
        "/api/v1/assets/",
        json={"type": "stock", "name": "Broker", "symbol": "NOPE", "quantity": 1},
    )

    body = (await client.post(f"{PRICE}/refresh-all")).json()

    assert body["refreshed"] == 0
    assert body["errors"] == 1
    assert body["error_details"][0]["symbol"] == "NOPE"


# --- Cache clearing ---


async def test_clearing_price_cache_keeps_recent_entries(client):
    """Current behavior: the optimized cleanup ignores max_age_days=0 and
    uses PRICE_CACHE_CLEANUP_DAYS, so only entries older than that go."""
    old = timedelta(days=settings.PRICE_CACHE_CLEANUP_DAYS + 1)
    await cache_price("AAPL", "stock", 100.0, age=timedelta(minutes=1))
    await cache_price("BTC", "crypto", 1.0, age=old)

    response = await client.delete(f"{PRICE}/cache")

    assert response.status_code == 200
    assert response.json() == {"message": "Cleared 1 cached price entries"}
    assert await count(PriceCache) == 1
