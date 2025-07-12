from sqlalchemy import Column, Integer, String, Float, Enum as PyEnum
from app.db.session import Base
import enum


class AssetType(str, enum.Enum):
    CASH = "cash"
    STOCK = "stock"
    CRYPTO = "crypto"


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(PyEnum(AssetType), nullable=False)

    # Common fields
    name = Column(
        String, index=True, nullable=False
    )  # e.g., "Bitcoin", "Apple Inc.", "Checking Account"
    quantity = Column(Float, nullable=False)

    # Optional fields
    symbol = Column(
        String, unique=True, index=True, nullable=True
    )  # e.g., "BTC", "AAPL"
    currency = Column(String, nullable=True)  # e.g., "EUR", "USD"
    purchase_price = Column(Float, nullable=True)
