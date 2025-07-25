"""
Schemas for cache management endpoints.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional


class CacheSettingsSchema(BaseModel):
    """
    Schema for cache settings.
    """

    price_cache_minutes: int
    conversion_cache_hours: int
    price_cache_cleanup_days: int
    conversion_cache_cleanup_days: int


class CacheStatsBaseSchema(BaseModel):
    """
    Base schema for cache statistics.
    """

    count: int = Field(..., description="Total number of cache entries")
    hit_count: int = Field(..., description="Number of cache hits")
    miss_count: int = Field(..., description="Number of cache misses")
    hit_rate: float = Field(..., description="Cache hit rate percentage")
    error: Optional[str] = Field(None, description="Error message if any")


class PriceCacheStatsSchema(CacheStatsBaseSchema):
    """
    Schema for price cache statistics.
    """

    average_age_minutes: int = Field(
        0, description="Average age of cache entries in minutes"
    )
    oldest_entry_minutes: int = Field(
        0, description="Age of oldest cache entry in minutes"
    )
    newest_entry_minutes: int = Field(
        0, description="Age of newest cache entry in minutes"
    )
    valid_entries: int = Field(
        0, description="Number of valid (non-expired) cache entries"
    )
    expired_entries: int = Field(0, description="Number of expired cache entries")
    by_asset_type: Dict[str, int] = Field(
        default_factory=dict, description="Distribution of cache entries by asset type"
    )
    by_source: Dict[str, int] = Field(
        default_factory=dict, description="Distribution of cache entries by source"
    )


class ConversionCacheStatsSchema(CacheStatsBaseSchema):
    """
    Schema for conversion cache statistics.
    """

    average_age_hours: float = Field(
        0, description="Average age of cache entries in hours"
    )
    oldest_entry_hours: float = Field(
        0, description="Age of oldest cache entry in hours"
    )
    newest_entry_hours: float = Field(
        0, description="Age of newest cache entry in hours"
    )
    valid_entries: int = Field(
        0, description="Number of valid (non-expired) cache entries"
    )
    expired_entries: int = Field(0, description="Number of expired cache entries")
    currency_pairs: int = Field(0, description="Number of unique currency pairs")
    by_source: Dict[str, int] = Field(
        default_factory=dict, description="Distribution of cache entries by source"
    )


class CacheStatsSchema(BaseModel):
    """
    Schema for overall cache statistics.
    """

    price_cache: PriceCacheStatsSchema
    conversion_cache: ConversionCacheStatsSchema
    cache_settings: CacheSettingsSchema


class CacheClearResponseSchema(BaseModel):
    """
    Schema for cache clearing response.
    """

    success: bool = Field(..., description="Whether the operation was successful")
    cleared_entries: int = Field(..., description="Number of cache entries cleared")
    error: Optional[str] = Field(None, description="Error message if any")
