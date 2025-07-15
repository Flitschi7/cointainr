from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


# --- Shared Conversion Cache Properties ---
class ConversionCacheBase(BaseModel):
    """
    Shared properties for ConversionCache schemas.
    """

    from_currency: str
    to_currency: str
    rate: float
    source: str = "exchangerate-api"


# --- Conversion Cache Creation Schema ---
class ConversionCacheCreate(ConversionCacheBase):
    """
    Properties required to create a ConversionCache entry.
    """

    pass


# --- Conversion Cache Read Schema ---
class ConversionCacheRead(ConversionCacheBase):
    """
    Properties to return via API when reading ConversionCache.
    """

    id: int
    fetched_at: datetime

    model_config = ConfigDict(from_attributes=True)
