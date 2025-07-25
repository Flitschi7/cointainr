"""
Database utilities for the application.

This module provides utilities for working with the database,
including dependency injection for database sessions.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import SessionLocal

# Use the default session maker from session.py
_current_session_maker = SessionLocal


def set_session_maker(session_maker: async_sessionmaker) -> None:
    """
    Set a custom session maker for the application.

    This allows replacing the default session maker with an optimized one.

    Args:
        session_maker: The new session maker to use
    """
    global _current_session_maker
    _current_session_maker = session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session as a dependency.

    This function is used as a FastAPI dependency to provide
    database sessions to endpoint functions.

    Yields:
        AsyncSession: A SQLAlchemy async session
    """
    async with _current_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
