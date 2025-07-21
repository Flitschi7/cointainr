"""
Database optimization utilities for Cointainr.

This module provides functions and configurations to optimize database performance,
including connection pooling, query optimization, and index management.
"""

import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy import event, Index, text
from app.core.config import settings
from app.db.session import engine, Base
from app.models.price_cache import PriceCache
from app.models.conversion_cache import ConversionCache

# Set up logger
logger = logging.getLogger(__name__)


def configure_connection_pooling():
    """
    Configure connection pooling for the SQLAlchemy engine.

    This function updates the engine configuration to use optimal connection pooling
    settings based on the application's needs.
    """
    # Connection pooling is already configured in the engine creation,
    # but we can optimize the pool size based on expected load

    # Get the database URL from settings
    database_url = settings.DATABASE_URL

    # Only apply pooling optimizations for non-SQLite databases
    # SQLite doesn't benefit from connection pooling in the same way
    if not database_url.startswith("sqlite"):
        logger.info("Configuring optimized connection pooling")

        # Create a new engine with optimized pooling settings
        optimized_engine = create_async_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=10,  # Number of connections to keep open
            max_overflow=20,  # Maximum number of connections to create beyond pool_size
            pool_timeout=30,  # Seconds to wait before timing out on getting a connection
            pool_recycle=1800,  # Recycle connections after 30 minutes
            pool_pre_ping=True,  # Check connection validity before using from pool
        )

        # Create a new sessionmaker with the optimized engine
        optimized_session_maker = async_sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=optimized_engine,
        )

        # Return the optimized session maker for use
        return optimized_session_maker

    logger.info("Using default connection settings for SQLite")
    return None


async def create_database_indexes():
    """
    Create optimized database indexes for frequently accessed fields.

    This function creates indexes on fields that are frequently used in WHERE clauses
    and JOIN conditions to improve query performance.
    """
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.db.session import SessionLocal

    logger.info("Creating optimized database indexes")

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
            logger.info("Database indexes created successfully")

        except Exception as e:
            await session.rollback()
            logger.error(f"Error creating database indexes: {e}")
            raise


async def optimize_database():
    """
    Perform database optimization tasks.

    This function runs various optimization tasks including:
    - Creating indexes
    - Configuring connection pooling
    - Running ANALYZE on SQLite databases
    """
    logger.info("Starting database optimization")

    # Create indexes for better query performance
    await create_database_indexes()

    # Configure connection pooling (if applicable)
    optimized_session = configure_connection_pooling()

    # For SQLite, run ANALYZE to optimize query planning
    if settings.DATABASE_URL.startswith("sqlite"):
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.db.session import SessionLocal

        async with SessionLocal() as session:
            try:
                logger.info("Running ANALYZE on SQLite database")
                await session.execute(text("ANALYZE"))
                await session.commit()
            except Exception as e:
                logger.warning(f"Could not run ANALYZE on SQLite database: {e}")

    logger.info("Database optimization completed")
    return optimized_session
