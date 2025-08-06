from sqlalchemy import Column, Integer, String, Float, Enum as PyEnum
from app.db.session import Base
import enum


class AssetType(str, enum.Enum):
    """
    Enum for supported asset types.
    """

    CASH = "cash"
    STOCK = "stock"
    CRYPTO = "crypto"
    DERIVATIVE = "derivative"


class Asset(Base):
    """
    SQLAlchemy model for financial assets.
    Represents cash, stocks, crypto, etc.
    """

    __tablename__ = "assets"

    # --- Primary Key ---
    id = Column(Integer, primary_key=True, index=True)

    # --- Asset Type ---
    type = Column(PyEnum(AssetType), nullable=False)

    # --- Common Fields ---
    name = Column(
        String, index=True, nullable=False
    )  # e.g., location name (e.g., "Depot 1", "Wallet")
    assetname = Column(
        String, index=True, nullable=True
    )  # e.g., "Apple Inc.", "Bitcoin", "AAPL", "BTC"
    quantity = Column(Float, nullable=False)

    # --- Optional Fields ---
    symbol = Column(String, index=True, nullable=True)  # e.g., "BTC", "AAPL"
    currency = Column(
        String, nullable=True
    )  # e.g., "EUR", "USD" (current price currency, usually USD)
    purchase_price = Column(Float, nullable=True)  # Purchase price per unit
    buy_currency = Column(
        String, nullable=True
    )  # Currency of purchase price (e.g., "EUR", "USD")
