# Cache Behavior Documentation

This document provides detailed information about the caching system in Cointainr, including implementation details, configuration options, and best practices for developers.

## Cache Architecture

The Cointainr application implements a multi-level caching strategy:

1. **Backend Database Cache**: Persistent cache stored in SQLite database
2. **Frontend Memory Cache**: In-memory cache for frontend components

### Backend Cache Structure

The backend cache is implemented using two main database tables:

- `price_cache`: Stores cached price data for assets
- `conversion_cache`: Stores cached currency conversion rates

### Frontend Cache Structure

The frontend cache is implemented using a centralized `CacheService` that provides:

- In-memory storage using JavaScript Map
- TTL-based cache invalidation
- Cache statistics tracking

## Cache Validation Logic

### Backend Cache Validation

```python
async def is_price_cache_valid(self, asset_id: str, force_refresh: bool = False) -> bool:
    """
    Determines if the price cache for an asset is valid.

    Args:
        asset_id: The asset ID to check
        force_refresh: If True, considers cache invalid regardless of age

    Returns:
        bool: True if cache is valid, False otherwise
    """
    if force_refresh:
        return False

    cache_entry = await self.get_price_cache_entry(asset_id)
    if not cache_entry:
        return False

    # Get TTL from environment or use default
    ttl_minutes = int(os.getenv("PRICE_CACHE_TTL_MINUTES", "15"))

    # Calculate age using timezone-aware datetime
    now = datetime.now(timezone.utc)
    cache_age = now - cache_entry.timestamp

    # Convert to minutes and compare with TTL
    cache_age_minutes = cache_age.total_seconds() / 60
    return cache_age_minutes <= ttl_minutes
```

### Frontend Cache Validation

```typescript
isCacheValid(key: string): boolean {
  const entry = this.cache.get(key);
  if (!entry) {
    return false;
  }

  const now = Date.now();
  const age = now - entry.timestamp;

  // Check if age exceeds TTL
  return age <= entry.ttl;
}
```

## Cache TTL Configuration

### Environment Variables

The cache Time-To-Live (TTL) settings are configurable via environment variables:

| Variable                     | Description                  | Default | Unit    |
| ---------------------------- | ---------------------------- | ------- | ------- |
| `PRICE_CACHE_TTL_MINUTES`    | TTL for price data           | 15      | Minutes |
| `CONVERSION_CACHE_TTL_HOURS` | TTL for conversion rates     | 24      | Hours   |
| `FORCE_REFRESH_ONLY`         | If true, always bypass cache | false   | Boolean |

### Example Configuration

```
# .env file
PRICE_CACHE_TTL_MINUTES=30
CONVERSION_CACHE_TTL_HOURS=12
FORCE_REFRESH_ONLY=false
```

## Cache Statistics

The cache system tracks various statistics to monitor performance:

### Backend Cache Statistics

- **Count**: Number of entries in cache
- **Average Age**: Average age of cache entries
- **Hit Rate**: Percentage of cache hits
- **Miss Rate**: Percentage of cache misses
- **Oldest Entry**: Age of the oldest cache entry
- **Newest Entry**: Age of the newest cache entry

### Frontend Cache Statistics

- **Hit Count**: Number of cache hits
- **Miss Count**: Number of cache misses
- **Hit Rate**: Percentage of cache hits
- **Entry Count**: Number of entries in cache
- **Average Age**: Average age of cache entries in milliseconds

## Force Refresh Mechanism

The force refresh mechanism allows bypassing the cache to fetch fresh data:

### Backend Implementation

```python
async def get_price_with_cache(self, asset_id: str, force_refresh: bool = False) -> PriceData:
    """
    Gets price data with caching support.

    Args:
        asset_id: The asset ID to get price for
        force_refresh: If True, bypasses cache and fetches fresh data

    Returns:
        PriceData: The price data
    """
    # Check cache validity
    is_valid = await self.cache_service.is_price_cache_valid(asset_id, force_refresh)

    if is_valid:
        # Return cached data
        cache_entry = await self.cache_service.get_price_cache_entry(asset_id)
        return PriceData(
            symbol=cache_entry.symbol,
            price=cache_entry.price,
            currency=cache_entry.currency,
            last_updated=cache_entry.timestamp,
            cached=True,
            cache_age=self._calculate_cache_age(cache_entry.timestamp)
        )

    # Fetch fresh data
    price_data = await self._fetch_price_from_external_api(asset_id)

    # Update cache
    await self.cache_service.update_price_cache(asset_id, price_data)

    return PriceData(
        symbol=price_data.symbol,
        price=price_data.price,
        currency=price_data.currency,
        last_updated=datetime.now(timezone.utc),
        cached=False,
        cache_age=0
    )
```

### Frontend Implementation

```typescript
async getOrFetch<T>(key: string, fetchFn: () => Promise<T>, options: CacheOptions): Promise<T> {
  const { ttl, forceRefresh = false } = options;

  // Check if we should use cache
  if (!forceRefresh && this.isCacheValid(key)) {
    this.hitCount++;
    const entry = this.cache.get(key);
    return entry.data;
  }

  // Cache miss or force refresh
  this.missCount++;

  try {
    // Fetch fresh data
    const data = await fetchFn();

    // Update cache
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      ttl,
      isStale: false
    });

    return data;
  } catch (error) {
    // If we have stale data, return it on error
    if (this.cache.has(key)) {
      const entry = this.cache.get(key);
      entry.isStale = true;
      return entry.data;
    }

    // No cached data available
    throw error;
  }
}
```

## Cache Keys

### Backend Cache Keys

- **Price Cache**: `{asset_id}`
- **Conversion Cache**: `{from_currency}_{to_currency}`

### Frontend Cache Keys

- **Price Cache**: `price_{type}_{symbol}`
- **Conversion Cache**: `conversion_{from}_{to}`
- **API Cache**: `api_{endpoint}_{params_hash}`

## Best Practices

### When to Use Cache

- **Use Cache**: For frequently accessed data that doesn't change often
- **Bypass Cache**: For critical operations requiring real-time data

### Cache Invalidation Strategies

1. **TTL-based**: Automatically invalidate cache after TTL expires
2. **Explicit**: Manually clear cache via API endpoints
3. **Event-based**: Invalidate cache when related data changes

### Error Handling with Cache

When external API calls fail:

1. Return cached data with staleness indicator
2. Log the error for monitoring
3. Implement retry logic with exponential backoff

### Cache Performance Optimization

- Use optimized database queries for cache lookups
- Implement connection pooling for database access
- Add database indexes for frequently accessed fields

## Troubleshooting

### Common Cache Issues

1. **Stale Data**: Check TTL settings and force refresh mechanism
2. **Cache Misses**: Verify cache key generation and storage
3. **Performance Issues**: Check database indexes and query optimization

### Debugging Cache

- Use cache statistics endpoints to monitor performance
- Check logs for cache-related errors
- Use health check endpoints to verify cache status
