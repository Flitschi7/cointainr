"""
Schemas for conversion endpoints.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime


class CacheStatusSchema(BaseModel):
    """
    Schema for cache status information.
    """

    is_valid: bool = Field(..., description="Whether the cache is valid")
    age_minutes: Optional[int] = Field(None, description="Age of cache in minutes")
    expires_at: Optional[str] = Field(
        None, description="When the cache expires (ISO format)"
    )
    ttl_hours: Optional[int] = Field(None, description="Cache TTL in hours")
    is_inverse_pair: Optional[bool] = Field(
        False, description="Whether this is an inverse currency pair"
    )
    using_expired_cache: Optional[bool] = Field(
        False, description="Whether using expired cache due to API failure"
    )


class ConversionRateSchema(BaseModel):
    """
    Schema for conversion rate response.
    """

    from_currency: str = Field(..., alias="from", description="Source currency code")
    to_currency: str = Field(..., alias="to", description="Target currency code")
    rate: float = Field(..., description="Conversion rate")
    cached: bool = Field(..., description="Whether this is from cache")
    fetched_at: datetime = Field(..., description="When this data was fetched")
    source: str = Field(..., description="Data source (e.g., 'exchangerate-api')")
    last_update: Optional[str] = Field(
        None, description="When the rate was last updated by the source"
    )
    next_update: Optional[str] = Field(
        None, description="When the rate will be updated next by the source"
    )
    cache_status: Optional[CacheStatusSchema] = Field(
        None, description="Cache status information"
    )

    class Config:
        populate_by_name = True


class ConversionAmountSchema(ConversionRateSchema):
    """
    Schema for amount conversion response.
    """

    amount: float = Field(..., description="Original amount")
    converted: float = Field(..., description="Converted amount")
