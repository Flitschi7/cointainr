from sqlalchemy import Column, Integer, String, Float, DateTime
from app.db.session import Base
from datetime import datetime


class ConversionCache(Base):
    """
    SQLAlchemy model for caching currency conversion rates.
    Stores conversion rates with timestamps to avoid excessive API calls.
    """

    __tablename__ = "conversion_cache"

    # --- Primary Key ---
    id = Column(Integer, primary_key=True, index=True)

    # --- Currency Pair ---
    from_currency = Column(String, nullable=False, index=True)
    to_currency = Column(String, nullable=False, index=True)

    # --- Conversion Data ---
    rate = Column(Float, nullable=False)

    # --- Cache Metadata ---
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    source = Column(String, nullable=False, default="exchangerate-api")

    def __repr__(self):
        return f"<ConversionCache(from={self.from_currency}, to={self.to_currency}, rate={self.rate}, fetched_at={self.fetched_at})>"
