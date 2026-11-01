"""
Holdings CRUD through the HTTP API, pinned to current behavior.

These tests describe what /api/v1/assets does today, including the absence of
value validation (item 10 adds rules). Name lookups go to fakes; no test may
reach a real provider.
"""

import httpx
import pytest
from sqlalchemy import text

import app.api.endpoints.price as price_endpoints
from app.api.endpoints import assets as assets_endpoints
from app.db.session import engine

ASSETS = "/api/v1/assets/"


class FakeTicker:
    info_by_symbol: dict[str, dict] = {}

    def __init__(self, symbol):
        self.info = self.info_by_symbol.get(symbol, {})


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def fake_coingecko(status_code, payload, calls):
    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def get(self, url):
            calls.append(url)
            return FakeResponse(status_code, payload)

    return FakeAsyncClient


@pytest.fixture(autouse=True)
def providers_unavailable(monkeypatch):
    """Every name source fails unless a test installs a fake."""

    def unavailable(*args, **kwargs):
        raise RuntimeError("provider unavailable in tests")

    async def unavailable_async(*args, **kwargs):
        raise RuntimeError("provider unavailable in tests")

    FakeTicker.info_by_symbol = {}
    monkeypatch.setattr(price_endpoints.finnhub_client, "symbol_lookup", unavailable)
    monkeypatch.setattr("yfinance.Ticker", unavailable)
    monkeypatch.setattr(
        assets_endpoints.onvista_service, "get_instrument_data", unavailable_async
    )
    monkeypatch.setattr(httpx, "AsyncClient", unavailable)


async def create(client, **fields):
    response = await client.post(ASSETS, json=fields)
    assert response.status_code == 200, response.text
    return response.json()


# --- Create ---


async def test_create_cash_holding_returns_it_with_id(client):
    body = await create(
        client, type="cash", name="Bank", quantity=2500.0, currency="EUR"
    )

    assert body["id"] > 0
    assert body == {
        "id": body["id"],
        "type": "cash",
        "name": "Bank",
        "assetname": "",
        "quantity": 2500.0,
        "symbol": None,
        "currency": "EUR",
        "purchase_price": None,
        "buy_currency": None,
    }


async def test_created_holding_is_listed(client):
    created = await create(client, type="cash", name="Bank", quantity=1.0)

    listed = (await client.get(ASSETS)).json()

    assert listed == [created]


async def test_asset_type_is_stored_by_enum_name(client):
    await create(client, type="crypto", name="Wallet", quantity=1.0)

    async with engine.connect() as conn:
        stored = (await conn.execute(text("SELECT type FROM assets"))).scalar_one()

    assert stored == "CRYPTO"


async def test_stock_name_comes_from_finnhub(client, monkeypatch):
    monkeypatch.setattr(
        price_endpoints.finnhub_client,
        "symbol_lookup",
        lambda symbol: {"count": 1, "result": [{"description": "APPLE INC"}]},
    )

    body = await create(client, type="stock", name="Broker", symbol="AAPL", quantity=3)

    assert body["assetname"] == "APPLE INC"


async def test_stock_name_falls_back_to_yahoo_when_finnhub_fails(client, monkeypatch):
    FakeTicker.info_by_symbol = {"AAPL": {"longName": "Apple Inc."}}
    monkeypatch.setattr("yfinance.Ticker", FakeTicker)

    body = await create(client, type="stock", name="Broker", symbol="AAPL", quantity=3)

    assert body["assetname"] == "Apple Inc."


async def test_stock_isin_name_comes_from_yahoo(client, monkeypatch):
    FakeTicker.info_by_symbol = {"US0378331005": {"shortName": "Apple"}}
    monkeypatch.setattr("yfinance.Ticker", FakeTicker)

    body = await create(
        client, type="stock", name="Broker", symbol="US0378331005", quantity=1
    )

    assert body["assetname"] == "Apple"


async def test_stock_name_falls_back_to_symbol_when_lookups_fail(client):
    body = await create(client, type="stock", name="Broker", symbol="XYZ", quantity=1)

    assert body["assetname"] == "XYZ"


async def test_crypto_name_comes_from_coingecko_by_mapped_id(client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        httpx, "AsyncClient", fake_coingecko(200, {"name": "Bitcoin"}, calls)
    )

    body = await create(
        client, type="crypto", name="Wallet", symbol="btc", quantity=0.5
    )

    assert body["assetname"] == "Bitcoin"
    assert calls == ["https://api.coingecko.com/api/v3/coins/bitcoin"]


async def test_crypto_name_falls_back_to_upper_symbol(client, monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", fake_coingecko(404, {}, []))

    body = await create(client, type="crypto", name="Wallet", symbol="abc", quantity=1)

    assert body["assetname"] == "ABC"


async def test_derivative_name_comes_from_onvista(client, monkeypatch):
    async def instrument(isin):
        return {"name": "Turbo Long DAX"}

    monkeypatch.setattr(
        assets_endpoints.onvista_service, "get_instrument_data", instrument
    )

    body = await create(
        client, type="derivative", name="Broker", symbol="DE000XX00000", quantity=10
    )

    assert body["assetname"] == "Turbo Long DAX"


async def test_derivative_name_falls_back_to_isin(client):
    body = await create(
        client, type="derivative", name="Broker", symbol="DE000XX00000", quantity=10
    )

    assert body["assetname"] == "DE000XX00000"


@pytest.mark.parametrize(
    "fields",
    [
        {"type": "bond", "name": "Broker", "quantity": 1},
        {"type": "STOCK", "name": "Broker", "quantity": 1},
        {"type": "cash", "quantity": 1},
        {"type": "cash", "name": "Bank"},
        {"type": "cash", "name": "Bank", "quantity": "lots"},
    ],
    ids=["unknown-type", "uppercase-type", "no-name", "no-quantity", "text-quantity"],
)
async def test_create_rejects_malformed_payload(client, fields):
    response = await client.post(ASSETS, json=fields)

    assert response.status_code == 422
    assert (await client.get(ASSETS)).json() == []


@pytest.mark.parametrize(
    "fields",
    [
        {"type": "cash", "name": "Bank", "quantity": -50.0},
        {"type": "cash", "name": "Bank", "quantity": 0},
        {"type": "stock", "name": "", "quantity": -1, "purchase_price": -5},
        {"type": "crypto", "name": "Wallet", "quantity": 1, "purchase_price": 0},
    ],
    ids=["negative-cash", "zero-quantity", "negative-stock", "free-acquisition"],
)
async def test_create_accepts_values_without_range_checks(client, fields):
    """Current behavior: no value rules yet (item 10 adds them)."""
    body = await create(client, **fields)

    assert body["quantity"] == fields["quantity"]


# --- Read ---


async def test_list_is_empty_without_holdings(client):
    response = await client.get(ASSETS)

    assert response.status_code == 200
    assert response.json() == []


async def test_list_supports_skip_and_limit(client):
    ids = [
        (await create(client, type="cash", name=f"Bank {i}", quantity=i))["id"]
        for i in range(5)
    ]

    page = (await client.get(ASSETS, params={"skip": 1, "limit": 2})).json()

    assert [a["id"] for a in page] == ids[1:3]


# --- Update ---


async def test_update_changes_only_sent_fields(client):
    created = await create(
        client,
        type="crypto",
        name="Wallet",
        symbol="BTC",
        quantity=0.1,
        currency="EUR",
        purchase_price=30000,
        buy_currency="EUR",
    )

    response = await client.put(f"{ASSETS}{created['id']}", json={"quantity": 0.25})

    assert response.status_code == 200
    assert response.json() == {**created, "quantity": 0.25}
    assert (await client.get(ASSETS)).json() == [{**created, "quantity": 0.25}]


async def test_update_can_clear_a_field_with_null(client):
    created = await create(
        client, type="cash", name="Bank", quantity=1, purchase_price=2.0
    )

    response = await client.put(
        f"{ASSETS}{created['id']}", json={"purchase_price": None}
    )

    assert response.json()["purchase_price"] is None


async def test_update_does_not_look_up_a_new_name(client):
    created = await create(
        client, type="stock", name="Broker", symbol="AAA", quantity=1
    )

    response = await client.put(f"{ASSETS}{created['id']}", json={"symbol": "BBB"})

    assert response.json()["symbol"] == "BBB"
    assert response.json()["assetname"] == "AAA"


async def test_update_unknown_holding_is_404(client):
    response = await client.put(f"{ASSETS}999", json={"quantity": 1})

    assert response.status_code == 404


async def test_update_rejects_unknown_type(client):
    created = await create(client, type="cash", name="Bank", quantity=1)

    response = await client.put(f"{ASSETS}{created['id']}", json={"type": "bond"})

    assert response.status_code == 422


# --- Delete ---


async def test_delete_returns_and_removes_the_holding(client):
    kept = await create(client, type="cash", name="Keep", quantity=1)
    gone = await create(client, type="cash", name="Gone", quantity=2)

    response = await client.delete(f"{ASSETS}{gone['id']}")

    assert response.status_code == 200
    assert response.json() == gone
    assert (await client.get(ASSETS)).json() == [kept]


async def test_delete_unknown_holding_is_404(client):
    response = await client.delete(f"{ASSETS}999")

    assert response.status_code == 404
