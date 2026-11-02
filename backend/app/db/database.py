"""
Database utilities for the application.

This module owns database sessions: `get_db` for request handlers and
`session_scope` for work outside a request (middleware, background tasks).
Nothing outside `app/db/` should create sessions from `SessionLocal`.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """
    Open a database session outside a request.

    The caller commits its own work; the session is closed on exit.

    Yields:
        AsyncSession: A SQLAlchemy async session
    """
    async with SessionLocal() as session:
        yield session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session as a dependency.

    This function is used as a FastAPI dependency to provide
    database sessions to endpoint functions. Pending changes are
    committed after the handler returns and rolled back if it raises.

    Yields:
        AsyncSession: A SQLAlchemy async session
    """
    async with session_scope() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
