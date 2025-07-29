from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.sql import func
from app.db.session import Base
from datetime import datetime, timedelta
from typing import Optional


class Session(Base):
    """
    SQLAlchemy model for user authentication sessions.
    Stores session tokens and manages session lifecycle.
    """

    __tablename__ = "sessions"

    # Primary key - session token (UUID-like string)
    id = Column(String, primary_key=True, index=True)

    # User identification
    username = Column(String, nullable=False, index=True)

    # Session timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # Session status
    is_active = Column(Boolean, default=True, nullable=False)

    # Optional: Last activity tracking
    last_activity = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Session(id={self.id}, username={self.username}, active={self.is_active})>"

    @property
    def is_expired(self) -> bool:
        """Check if the session has expired"""
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if the session is valid (active and not expired)"""
        return self.is_active and not self.is_expired

    @classmethod
    def create_expiry_time(cls, hours: int = 24) -> datetime:
        """Create an expiry time for a new session"""
        return datetime.utcnow() + timedelta(hours=hours)
