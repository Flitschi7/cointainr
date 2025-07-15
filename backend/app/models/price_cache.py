from sqlalchemy import Column, Integer, String, Float, DateTime
from app.db.session import Base
from datetime import datetime


class PriceCache(Base):
    """
    SQLAlchemy model for caching asset prices.
    Stores fetched prices with timestamps to avoid excessive API calls.
    """

    __tablename__ = "price_cache"

    # --- Primary Key ---
    id = Column(Integer, primary_key=True, index=True)

    # --- Asset Identifier ---
    symbol = Column(String, nullable=False, index=True)  # Stock symbol or crypto symbol
    asset_type = Column(String, nullable=False)  # 'stock' or 'crypto'

    # --- Price Data ---
    price = Column(Float, nullable=False)
    currency = Column(String, nullable=False)

    # --- Cache Metadata ---
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    source = Column(String, nullable=False)  # 'finnhub', 'yfinance', 'coingecko', etc.

    def __repr__(self):
        return f"<PriceCache(symbol={self.symbol}, price={self.price}, currency={self.currency}, fetched_at={self.fetched_at})>"
