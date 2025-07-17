"""
Database utilities for the application.

This module provides utilities for working with the database,
including dependency injection for database sessions.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session as a dependency.

    This function is used as a FastAPI dependency to provide
    database sessions to endpoint functions.

    Yields:
        AsyncSession: A SQLAlchemy async session
    """
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
