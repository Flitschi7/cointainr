"""
Database optimization utilities for Cointainr.

This module provides functions and configurations to optimize database performance,
including connection pooling, query optimization, and index management.
"""

import logging
from sqlalchemy import Index, text
from app.core.config import settings
from app.models.price_cache import PriceCache
from app.models.conversion_cache import ConversionCache

# Set up logger
logger = logging.getLogger(__name__)


async def create_database_indexes():
    """
    Create optimized database indexes for frequently accessed fields.

    This function creates indexes on fields that are frequently used in WHERE clauses
    and JOIN conditions to improve query performance.
    """
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.db.session import SessionLocal

    logger.debug("Creating optimized database indexes")

    async with SessionLocal() as session:
        try:
            # For SQLite, we need to use raw SQL for some index operations
            is_sqlite = settings.DATABASE_URL.startswith("sqlite")

            if is_sqlite:
                # Create indexes using raw SQL for SQLite
                # These indexes will improve query performance for common operations

                # Index for price cache lookups by symbol and asset_type
                await session.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS idx_price_cache_symbol_type ON price_cache (symbol, asset_type)"
                    )
                )

                # Index for price cache lookups by fetched_at (for TTL checks)
                await session.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS idx_price_cache_fetched_at ON price_cache (fetched_at)"
                    )
                )

                # Index for conversion cache lookups by currency pair
                await session.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS idx_conversion_cache_currencies ON conversion_cache (from_currency, to_currency)"
                    )
                )

                # Index for conversion cache lookups by fetched_at (for TTL checks)
                await session.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS idx_conversion_cache_fetched_at ON conversion_cache (fetched_at)"
                    )
                )

            else:
                # For other databases, we can use SQLAlchemy's Index objects
                # These will be created when the tables are created

                # Define indexes that will be created
                indexes = [
                    Index(
                        "idx_price_cache_symbol_type",
                        PriceCache.symbol,
                        PriceCache.asset_type,
                    ),
                    Index("idx_price_cache_fetched_at", PriceCache.fetched_at),
                    Index(
                        "idx_conversion_cache_currencies",
                        ConversionCache.from_currency,
                        ConversionCache.to_currency,
                    ),
                    Index(
                        "idx_conversion_cache_fetched_at", ConversionCache.fetched_at
                    ),
                ]

                # Create each index if it doesn't exist
                for index in indexes:
                    try:
                        await session.execute(
                            text(
                                f"CREATE INDEX IF NOT EXISTS {index.name} ON {index.table.name} ({', '.join(c.name for c in index.columns)})"
                            )
                        )
                    except Exception as e:
                        logger.warning(f"Could not create index {index.name}: {e}")

            await session.commit()
            logger.debug("Database indexes created successfully")

        except Exception as e:
            await session.rollback()
            logger.error(f"Error creating database indexes: {e}")
            raise


async def optimize_database():
    """
    Perform database optimization tasks.

    This function runs various optimization tasks including:
    - Creating indexes for better query performance
    - Running ANALYZE on SQLite databases for query plan optimization
    """
    logger.debug("Starting database optimization")

    # Create indexes for better query performance
    await create_database_indexes()

    # For SQLite, run ANALYZE to optimize query planning
    if settings.DATABASE_URL.startswith("sqlite"):
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.db.session import SessionLocal

        async with SessionLocal() as session:
            try:
                logger.debug("Running ANALYZE on SQLite database")
                await session.execute(text("ANALYZE"))
                await session.commit()
            except Exception as e:
                logger.warning(f"Could not run ANALYZE on SQLite database: {e}")

    logger.debug("Database optimization completed")
