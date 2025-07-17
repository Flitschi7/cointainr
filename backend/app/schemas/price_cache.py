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

    def is_cache_valid(self) -> bool:
        """
        Check if this cache entry is still valid based on current cache settings.

        Returns:
            bool: True if cache is still valid, False if expired
        """
        from app.services.cache_management import cache_management_service

        return cache_management_service.is_price_cache_valid(self)

    def get_cache_expiration(self) -> Optional[datetime]:
        """
        Get the expiration datetime for this cache entry.

        Returns:
            datetime: When this cache entry expires, or None if invalid
        """
        from app.services.cache_management import cache_management_service

        return cache_management_service.get_price_cache_expiration(self)

    def get_cache_age_minutes(self) -> Optional[int]:
        """
        Get the age of this cache entry in minutes.

        Returns:
            int: Age in minutes, or None if invalid
        """
        from app.services.cache_management import cache_management_service

        return cache_management_service.get_cache_age_minutes(self)


# --- Price Cache Update Schema ---
class PriceCacheUpdate(BaseModel):
    """
    Properties that can be updated for a PriceCache entry.
    """

    price: Optional[float] = None
    currency: Optional[str] = None
    source: Optional[str] = None
