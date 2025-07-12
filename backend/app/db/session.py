from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

# The database URL for a local SQLite file named cointainr.db
DATABASE_URL = "sqlite+aiosqlite:///./cointainr.db"

# Create the SQLAlchemy engine
# connect_args is needed for SQLite to enforce foreign key constraints
engine = create_async_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Create a configured "Session" class
# This will be our handle to the database
SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for our database models
# All our models will inherit from this class
Base = declarative_base()
