import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

# --- Database Configuration ---


def get_database_url() -> str:
    """
    Get the database URL from environment variable or use default SQLite file.
    """
    return os.getenv("COINTAINR_DATABASE_URL", "sqlite+aiosqlite:///./cointainr.db")


DATABASE_URL = get_database_url()

# --- Engine & Session Setup ---

# Create the SQLAlchemy async engine
engine = create_async_engine(
    DATABASE_URL,
    connect_args=(
        {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    ),
)

# Create a configured async sessionmaker
SessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# --- Base Model ---

Base = declarative_base()
