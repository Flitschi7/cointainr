# Cache Service Documentation

## Overview

The Cache Service provides a centralized caching mechanism for the frontend application. It implements a cache-first strategy to reduce API calls, improve performance, and respect API rate limits.

## Features

- Generic caching with TTL (Time-To-Live) support
- Cache validation and staleness indicators
- Cache statistics tracking (hits, misses, age)
- Support for force refresh to bypass cache
- Fallback to cached data when API calls fail
- Batch operation support

## Usage Examples

### Basic Usage

```typescript
import { cacheService } from '$lib/services';

// Get data with caching
const data = await cacheService.getOrFetch(
	'my-cache-key',
	async () => {
		// This function only runs if cache is invalid or force refresh is true
		const response = await fetch('https://api.example.com/data');
		return await response.json();
	},
	{ ttl: 60000 } // 1 minute TTL
);
```

### With Force Refresh

```typescript
// Force refresh to bypass cache
const freshData = await cacheService.getOrFetch('my-cache-key', fetchFunction, {
	forceRefresh: true
});
```

### Checking Cache Status

```typescript
// Check if cache is valid
const isValid = cacheService.isCacheValid('my-cache-key');

// Get cache age
const ageMs = cacheService.getCacheAge('my-cache-key');
const formattedAge = cacheService.formatCacheAge('my-cache-key'); // "2 minutes ago"

// Get time until expiration
const expiryMs = cacheService.getTimeUntilExpiration('my-cache-key');
const formattedExpiry = cacheService.formatTimeUntilExpiration('my-cache-key'); // "Expires in 13 minutes"
```

### Cache Management

```typescript
// Clear specific cache entry
cacheService.clearCache('my-cache-key');

// Clear all cache entries with a prefix
cacheService.clearCacheByPrefix('price:');

// Clear all cache
cacheService.clearAllCache();
```

### Cache Statistics

```typescript
// Get overall cache statistics
const stats = cacheService.getCacheStats();
console.log(`Cache entries: ${stats.count}`);
console.log(`Average age: ${stats.averageAge}ms`);
console.log(`Hit rate: ${stats.hitRate * 100}%`);

// Get statistics for a specific category
const priceStats = cacheService.getCacheStats('price:');
```

## Cache Key Conventions

For consistent cache keys, use the utility functions in `cacheKeys.ts`:

```typescript
import { getPriceCacheKey, getConversionCacheKey } from '$lib/utils/cacheKeys';

// Generate cache key for price data
const priceKey = getPriceCacheKey('crypto', 'BTC');

// Generate cache key for conversion rate
const conversionKey = getConversionCacheKey('USD', 'EUR');
```

## Environment Configuration

Cache TTL settings can be configured through environment variables:

- `VITE_PRICE_CACHE_TTL_MINUTES`: TTL for price cache in minutes (default: 15)
- `VITE_CONVERSION_CACHE_TTL_HOURS`: TTL for conversion cache in hours (default: 24)
- `VITE_FORCE_REFRESH_ONLY`: If set to 'true', always bypass cache (default: false)
- `VITE_DEFAULT_CURRENCY`: Default currency for display (default: 'USD')

Access these settings through the environment utility:

```typescript
import { getPriceCacheTTL, getConversionCacheTTL } from '$lib/utils/environment';

const priceTTL = getPriceCacheTTL();
const conversionTTL = getConversionCacheTTL();
```
