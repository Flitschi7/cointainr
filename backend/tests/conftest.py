"""
Shared test setup.

The app reads its configuration at import time, so the environment is fixed
here, before anything from `app` is imported: a temporary SQLite file,
placeholder provider keys, and authentication off. Values already set in the
process environment win over a local `.env`, so a developer's real keys or
credentials are never picked up.
"""

import os
import socket
import tempfile
from pathlib import Path

_TEST_DB = Path(tempfile.mkdtemp(prefix="cointainr-tests-")) / "test.db"
_TEST_ENV = {
    "COINTAINR_DATABASE_URL": f"sqlite+aiosqlite:///{_TEST_DB.as_posix()}",
    "FINNHUB_API_KEY": "test-placeholder",
    "EXCHANGERATE_API_KEY": "test-placeholder",
    "FORCE_REFRESH_ONLY": "true",
    "AUTH_USER": "",
    "AUTH_PASSWORD": "",
    "DEMO_MODE": "false",
    "ENVIRONMENT": "test",
    "LOG_LEVEL": "WARNING",
}
os.environ.update(_TEST_ENV)

import httpx  # noqa: E402
import pytest  # noqa: E402

from app.db.session import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

# Kept before any test patches httpx.AsyncClient to fake a provider.
RealAsyncClient = httpx.AsyncClient

_LOOPBACK = {"127.0.0.1", "::1", "localhost"}
_real_connect = socket.socket.connect


def _guarded_connect(sock, address):
    host = address[0] if isinstance(address, tuple) else address
    if host not in _LOOPBACK:
        raise RuntimeError(f"Network access blocked in tests: {address!r}")
    return _real_connect(sock, address)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Fail any test that tries to reach a real market-data provider."""
    monkeypatch.setattr(socket.socket, "connect", _guarded_connect)


@pytest.fixture
async def db_tables():
    """Fresh, empty tables in the temporary database for each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest.fixture
async def client(db_tables):
    """In-process API client. The app lifespan (scheduled tasks) is not run."""
    transport = httpx.ASGITransport(app=app)
    async with RealAsyncClient(transport=transport, base_url="http://test") as c:
        yield c
