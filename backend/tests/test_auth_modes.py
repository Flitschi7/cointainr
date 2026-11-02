"""
Authentication off, on, and demo mode, pinned to current behavior.

The middleware is installed when `create_app()` runs and reads the shared
`auth_settings` on each request, so each test patches that object and builds
a fresh app. Credentials here are test values only.
"""

import secrets
from datetime import datetime, timedelta

import httpx
import pytest
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.auth_config import AuthSettings, auth_settings
from app.db.session import engine
from app.main import create_app
from app.models.asset import Asset, AssetType
from app.models.conversion_cache import ConversionCache
from app.models.price_cache import PriceCache
from app.models.session import Session as AuthSession
from app.services.auth_service import auth_service
from app.services.demo_service import demo_service

ASSETS = "/api/v1/assets/"
AUTH = "/api/v1/auth"
USER, PASSWORD = "tester", "test-password"

Session = async_sessionmaker(engine, expire_on_commit=False)


def set_mode(monkeypatch, mode):
    users = {
        "off": ("", "", False),
        "on": (USER, PASSWORD, False),
        "demo": ("demo", "demo1", True),
    }
    user, password, demo = users[mode]
    monkeypatch.setattr(auth_settings, "AUTH_USER", user)
    monkeypatch.setattr(auth_settings, "AUTH_PASSWORD", password)
    monkeypatch.setattr(auth_settings, "DEMO_MODE", demo)


@pytest.fixture
async def make_client(db_tables, monkeypatch):
    clients = []

    async def _make(mode):
        set_mode(monkeypatch, mode)
        transport = httpx.ASGITransport(app=create_app())
        c = httpx.AsyncClient(transport=transport, base_url="http://test")
        clients.append(c)
        return c

    yield _make
    for c in clients:
        await c.aclose()


async def login(client, username=USER, password=PASSWORD):
    return await client.post(
        f"{AUTH}/login", json={"username": username, "password": password}
    )


async def add_asset(**fields):
    async with Session() as session:
        session.add(Asset(**fields))
        await session.commit()


async def count(model):
    async with Session() as session:
        return (await session.execute(select(func.count()).select_from(model))).scalar()


# --- Configuration ---


@pytest.mark.parametrize(
    "env, enabled",
    [
        ({}, False),
        ({"AUTH_USER": "u"}, False),
        ({"AUTH_USER": "u", "AUTH_PASSWORD": "p"}, True),
        ({"DEMO_MODE": "true"}, True),
        ({"DEMO_MODE": "yes"}, True),
        ({"DEMO_MODE": "off"}, False),
    ],
    ids=["nothing", "user-only", "user-and-password", "demo", "demo-yes", "demo-off"],
)
def test_auth_is_enabled_by_both_credentials_or_demo(monkeypatch, env, enabled):
    for name in ("AUTH_USER", "AUTH_PASSWORD", "DEMO_MODE"):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)

    assert AuthSettings().auth_enabled is enabled


def test_demo_mode_overrides_configured_credentials(monkeypatch):
    monkeypatch.setenv("AUTH_USER", "someone")
    monkeypatch.setenv("AUTH_PASSWORD", "secret")
    monkeypatch.setenv("DEMO_MODE", "true")

    settings = AuthSettings()

    assert (settings.AUTH_USER, settings.AUTH_PASSWORD) == ("demo", "demo1")


@pytest.mark.parametrize(
    "username, password, valid",
    [
        (USER, PASSWORD, True),
        (USER, "wrong", False),
        ("someone", PASSWORD, False),
        (USER, "", False),
        ("", "", False),
        (USER, "pässwört", False),
    ],
    ids=["valid", "wrong-password", "wrong-user", "empty-password", "empty", "non-ascii"],
)
async def test_credentials_are_checked(monkeypatch, username, password, valid):
    set_mode(monkeypatch, "on")

    assert await auth_service.validate_credentials(username, password) is valid


async def test_credentials_are_compared_in_constant_time(monkeypatch):
    set_mode(monkeypatch, "on")
    compared = []
    real = secrets.compare_digest

    def spy(a, b):
        compared.append((a, b))
        return real(a, b)

    monkeypatch.setattr(secrets, "compare_digest", spy)

    await auth_service.validate_credentials("someone", "wrong")

    assert compared == [
        (b"someone", USER.encode()),
        (b"wrong", PASSWORD.encode()),
    ]


# --- Auth off ---


async def test_off_api_is_open_without_session(make_client):
    client = await make_client("off")

    assert (await client.get(ASSETS)).status_code == 200


async def test_off_reports_auth_disabled(make_client):
    client = await make_client("off")

    config = (await client.get(f"{AUTH}/config")).json()
    status = (await client.get(f"{AUTH}/status")).json()

    assert config["auth_enabled"] is False
    assert config["demo_mode"] is False
    assert status["authenticated"] is False


async def test_off_login_and_demo_credentials_are_unavailable(make_client):
    client = await make_client("off")

    assert (await login(client)).status_code == 503
    assert (await client.get(f"{AUTH}/demo-credentials")).status_code == 503


# --- Auth on ---


async def test_on_api_requires_a_session(make_client):
    client = await make_client("on")

    response = await client.get(ASSETS)

    assert response.status_code == 401
    assert response.json()["error_code"] == "AUTH_REQUIRED"


@pytest.mark.parametrize(
    "path",
    ["/api/health", f"{AUTH}/config", f"{AUTH}/status", "/_app/x.js", "/favicon.ico"],
)
async def test_on_public_paths_skip_the_session_check(make_client, path):
    client = await make_client("on")

    response = await client.get(path)

    assert response.status_code != 401


async def test_on_wrong_password_is_refused_without_cookie(make_client):
    client = await make_client("on")

    response = await login(client, password="wrong")

    assert response.status_code == 200
    assert response.json()["success"] is False
    assert "session_token" not in response.cookies
    assert await count(AuthSession) == 0


async def test_on_login_sets_http_only_cookie_and_opens_api(make_client):
    client = await make_client("on")

    response = await login(client)

    assert response.json()["success"] is True
    cookie = response.headers["set-cookie"].lower()
    assert "session_token=" in cookie
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "secure" not in cookie  # ENVIRONMENT is "test", not production
    assert (await client.get(ASSETS)).status_code == 200


async def test_on_login_cookie_is_secure_in_production(make_client, monkeypatch):
    client = await make_client("on")
    monkeypatch.setattr(auth_settings, "ENVIRONMENT", "production")

    response = await login(client)

    assert "secure" in response.headers["set-cookie"].lower()


@pytest.mark.parametrize("header", ["Authorization", "X-Session-Token"])
async def test_on_session_token_is_accepted_in_headers(make_client, header):
    client = await make_client("on")
    token = (await login(client)).json()["session_token"]
    client.cookies.clear()
    value = f"Bearer {token}" if header == "Authorization" else token

    response = await client.get(ASSETS, headers={header: value})

    assert response.status_code == 200


async def test_on_status_reports_logged_in_user(make_client):
    client = await make_client("on")
    await login(client)

    status = (await client.get(f"{AUTH}/status")).json()

    assert status["authenticated"] is True
    assert status["session_valid"] is True
    assert status["username"] == USER


async def test_on_logout_ends_the_session(make_client):
    client = await make_client("on")
    token = (await login(client)).json()["session_token"]

    response = await client.post(f"{AUTH}/logout")

    assert response.json()["success"] is True
    client.cookies.clear()
    assert (
        await client.get(ASSETS, headers={"X-Session-Token": token})
    ).status_code == 401


async def test_on_expired_session_is_refused(make_client):
    client = await make_client("on")
    await login(client)
    async with Session() as session:
        await session.execute(
            update(AuthSession).values(
                expires_at=datetime.utcnow() - timedelta(minutes=1)
            )
        )
        await session.commit()

    response = await client.get(ASSETS)

    assert response.status_code == 401


async def test_on_unknown_token_is_refused(make_client):
    client = await make_client("on")

    response = await client.get(ASSETS, headers={"X-Session-Token": "not-a-session"})

    assert response.status_code == 401


async def test_on_demo_credentials_are_not_offered(make_client):
    client = await make_client("on")

    assert (await client.get(f"{AUTH}/demo-credentials")).status_code == 404


# --- Demo mode ---


async def test_demo_offers_and_accepts_demo_credentials(make_client):
    client = await make_client("demo")

    offered = (await client.get(f"{AUTH}/demo-credentials")).json()
    logged_in = (await login(client, "demo", "demo1")).json()

    assert offered["credentials"] == {"username": "demo", "password": "demo1"}
    assert logged_in["success"] is True
    assert logged_in["demo_mode"] is True
    assert (await client.get(ASSETS)).status_code == 200


async def test_demo_api_still_requires_a_session(make_client):
    client = await make_client("demo")

    assert (await client.get(ASSETS)).status_code == 401


async def test_demo_cleanup_keeps_only_the_preserved_holding(make_client):
    await make_client("demo")
    await add_asset(id=1, type=AssetType.CASH, name="Demo", quantity=1000)
    await add_asset(id=2, type=AssetType.STOCK, name="Visitor", quantity=5)
    async with Session() as session:
        session.add(
            PriceCache(
                symbol="AAPL", asset_type="stock", price=1, currency="USD", source="s"
            )
        )
        session.add(ConversionCache(from_currency="USD", to_currency="EUR", rate=1))
        await session.commit()

    assert await demo_service.cleanup_database() is True

    async with Session() as session:
        ids = (await session.execute(select(Asset.id))).scalars().all()
    assert ids == [1]
    assert await count(PriceCache) == 0
    assert await count(ConversionCache) == 0


async def test_cleanup_outside_demo_mode_deletes_nothing(make_client):
    await make_client("on")
    await add_asset(id=1, type=AssetType.CASH, name="Bank", quantity=1)
    await add_asset(id=2, type=AssetType.STOCK, name="Broker", quantity=5)

    assert await demo_service.cleanup_database() is False

    assert await count(Asset) == 2


async def test_demo_seeds_the_preserved_holding_only_in_demo_mode(make_client):
    await make_client("on")
    await demo_service.ensure_demo_asset_exists()
    assert await count(Asset) == 0

    await make_client("demo")
    await demo_service.ensure_demo_asset_exists()
    async with Session() as session:
        asset = (await session.execute(select(Asset))).scalar_one()
    assert (asset.id, asset.name, asset.quantity) == (1, "Demo Cash", 1000.0)
