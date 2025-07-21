"""
Pytest configuration file for backend tests.

This file contains fixtures and configuration for pytest tests.
"""

import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.db.session import Base
from app.core.config import settings

# Use in-memory SQLite database for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create async engine for tests
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=NullPool,
)

# Create async session factory
TestingSessionLocal = sessionmaker(
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


@pytest.fixture(scope="session")
def event_loop():
    """
    Create an instance of the default event loop for each test case.
    This is needed for pytest-asyncio.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def setup_database():
    """
    Create all tables in the test database.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session(setup_database) -> AsyncGenerator[AsyncSession, None]:
    """
    Create a fresh database session for a test.

    We need to ensure that the database is set up before we yield the session.
    """
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client_session(db_session):
    """
    Create a test client with a database session.
    """
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.deps import get_db

    # Override the get_db dependency to use our test database
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    # Remove the override after the test
    app.dependency_overrides.clear()
