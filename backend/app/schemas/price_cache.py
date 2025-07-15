from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


# --- Shared Price Cache Properties ---
class PriceCacheBase(BaseModel):
    """
    Shared properties for PriceCache schemas.
    """

    symbol: str
    asset_type: str
    price: float
    currency: str
    source: str


# --- Price Cache Creation Schema ---
class PriceCacheCreate(PriceCacheBase):
    """
    Properties required to create a PriceCache entry.
    """

    pass


# --- Price Cache Read Schema ---
class PriceCacheRead(PriceCacheBase):
    """
    Properties to return via API when reading PriceCache.
    """

    id: int
    fetched_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Price Cache Update Schema ---
class PriceCacheUpdate(BaseModel):
    """
    Properties that can be updated for a PriceCache entry.
    """

    price: Optional[float] = None
    currency: Optional[str] = None
    source: Optional[str] = None
