# Cointainr API Documentation

This document provides comprehensive documentation for all API endpoints in the Cointainr application, with a focus on cache behavior and error handling.

## Table of Contents

1. [Cache Endpoints](#cache-endpoints)
2. [Conversion Endpoints](#conversion-endpoints)
3. [Price Endpoints](#price-endpoints)
4. [Asset Endpoints](#asset-endpoints)
5. [Performance Monitoring Endpoints](#performance-monitoring-endpoints)
6. [Health Check Endpoints](#health-check-endpoints)
7. [Error Handling](#error-handling)
8. [Cache Behavior](#cache-behavior)

## Cache Endpoints

### Get Conversion Cache Statistics

Retrieves statistics about the conversion rate cache.

```
GET /cache/conversion/stats
```

**Response Schema:** `CacheStatsSchema`

**Example Response:**

```json
{
  "conversion_cache": {
    "count": 12,
    "average_age_hours": 5.2,
    "oldest_entry_hours": 23.1,
    "newest_entry_hours": 0.5,
    "hit_rate": 0.85,
    "miss_rate": 0.15
  }
}
```

**Cache Behavior:**

- This endpoint does not use cache itself
- Returns statistics about the current state of the conversion cache

**Error Responses:**

- `500 Internal Server Error` - Database connection issues

### Clear Price Cache

Clears all cached price data.

```
POST /cache/clear/prices
```

**Response Schema:** `CacheClearResponseSchema`

**Example Response:**

```json
{
  "success": true,
  "cleared_entries": 45
}
```

**Cache Behavior:**

- This endpoint invalidates all price cache entries
- Forces fresh data to be fetched on next price request

**Error Responses:**

- `500 Internal Server Error` - Database operation failure

### Clear Conversion Cache

Clears all cached currency conversion rates.

```
POST /cache/clear/conversion
```

**Response Schema:** `CacheClearResponseSchema`

**Example Response:**

```json
{
  "success": true,
  "cleared_entries": 8
}
```

**Cache Behavior:**

- This endpoint invalidates all conversion cache entries
- Forces fresh conversion rates to be fetched on next request

**Error Responses:**

- `500 Internal Server Error` - Database operation failure

## Conversion Endpoints

### Get Conversion Rate

Retrieves the conversion rate between two currencies.

```
GET /conversion/rate
```

**Query Parameters:**

- `from_currency` (required): Source currency code (e.g., USD)
- `to_currency` (required): Target currency code (e.g., EUR)
- `force_refresh` (optional): Boolean flag to bypass cache (default: false)

**Response Schema:** `ConversionRateSchema`

**Example Response:**

```json
{
  "from_currency": "USD",
  "to_currency": "EUR",
  "rate": 0.92,
  "last_updated": "2025-07-19T10:15:30Z",
  "cached": true,
  "cache_age": 3.5
}
```

**Cache Behavior:**

- Uses cached conversion rate if available and not expired
- Cache TTL is controlled by `CONVERSION_CACHE_TTL_HOURS` environment variable
- When `force_refresh=true`, bypasses cache and fetches fresh data
- Updates cache with new data after successful external API call

**Error Responses:**

- `400 Bad Request` - Invalid currency codes
- `404 Not Found` - Conversion rate not available
- `429 Too Many Requests` - API rate limit exceeded
- `500 Internal Server Error` - External API failure or database issues
- `503 Service Unavailable` - External service unavailable

## Price Endpoints

### Get Stock Price

Retrieves the current price for a stock.

```
GET /stock/{identifier}
```

**Path Parameters:**

- `identifier` (required): Stock symbol (e.g., AAPL)

**Query Parameters:**

- `force_refresh` (optional): Boolean flag to bypass cache (default: false)

**Response Schema:** `PriceDataSchema`

**Example Response:**

```json
{
  "symbol": "AAPL",
  "price": 185.92,
  "currency": "USD",
  "last_updated": "2025-07-19T10:15:30Z",
  "cached": true,
  "cache_age": 8.5
}
```

**Cache Behavior:**

- Uses cached price data if available and not expired
- Cache TTL is controlled by `PRICE_CACHE_TTL_MINUTES` environment variable
- When `force_refresh=true`, bypasses cache and fetches fresh data
- Updates cache with new data after successful external API call

**Error Responses:**

- `400 Bad Request` - Invalid stock symbol
- `404 Not Found` - Stock not found
- `429 Too Many Requests` - API rate limit exceeded
- `500 Internal Server Error` - External API failure or database issues
- `503 Service Unavailable` - External service unavailable

### Get Crypto Price

Retrieves the current price for a cryptocurrency.

```
GET /crypto/{symbol}
```

**Path Parameters:**

- `symbol` (required): Cryptocurrency symbol (e.g., BTC)

**Query Parameters:**

- `force_refresh` (optional): Boolean flag to bypass cache (default: false)

**Response Schema:** `PriceDataSchema`

**Example Response:**

```json
{
  "symbol": "BTC",
  "price": 65432.1,
  "currency": "USD",
  "last_updated": "2025-07-19T10:15:30Z",
  "cached": true,
  "cache_age": 2.5
}
```

**Cache Behavior:**

- Uses cached price data if available and not expired
- Cache TTL is controlled by `PRICE_CACHE_TTL_MINUTES` environment variable
- When `force_refresh=true`, bypasses cache and fetches fresh data
- Updates cache with new data after successful external API call

**Error Responses:**

- `400 Bad Request` - Invalid cryptocurrency symbol
- `404 Not Found` - Cryptocurrency not found
- `429 Too Many Requests` - API rate limit exceeded
- `500 Internal Server Error` - External API failure or database issues
- `503 Service Unavailable` - External service unavailable

### Convert Currency

Converts an amount from one currency to another.

```
GET /price/convert
```

**Query Parameters:**

- `from_currency` (required): Source currency code
- `to_currency` (required): Target currency code
- `amount` (required): Amount to convert
- `force_refresh` (optional): Boolean flag to bypass cache (default: false)

**Example Response:**

```json
{
  "from_currency": "USD",
  "to_currency": "EUR",
  "original_amount": 100,
  "converted_amount": 92,
  "rate": 0.92,
  "cached": true,
  "cache_age": 3.5
}
```

**Cache Behavior:**

- Uses cached conversion rate if available and not expired
- Cache TTL is controlled by `CONVERSION_CACHE_TTL_HOURS` environment variable
- When `force_refresh=true`, bypasses cache and fetches fresh data
- Updates cache with new data after successful external API call

**Error Responses:**

- `400 Bad Request` - Invalid currency codes or amount
- `404 Not Found` - Conversion rate not available
- `429 Too Many Requests` - API rate limit exceeded
- `500 Internal Server Error` - External API failure or database issues

### Refresh All Prices

Refreshes all cached price data.

```
POST /price/refresh-all
```

**Response:**

```json
{
  "success": true,
  "refreshed_count": 15,
  "failed_count": 0
}
```

**Cache Behavior:**

- Invalidates all price cache entries
- Fetches fresh data for all tracked assets
- Updates cache with new data

**Error Responses:**

- `500 Internal Server Error` - Database operation failure or external API issues

### Get Asset Cache Status

Retrieves the cache status for all tracked assets.

```
GET /price/cache/asset-status
```

**Response:**

```json
{
  "assets": [
    {
      "asset_id": "1",
      "symbol": "AAPL",
      "type": "stock",
      "cached": true,
      "cache_age_minutes": 8,
      "cache_valid": true
    },
    {
      "asset_id": "2",
      "symbol": "BTC",
      "type": "crypto",
      "cached": true,
      "cache_age_minutes": 3,
      "cache_valid": true
    }
  ]
}
```

**Cache Behavior:**

- This endpoint does not use cache itself
- Returns information about cache status for each asset

**Error Responses:**

- `500 Internal Server Error` - Database operation failure

## Asset Endpoints

### Create Asset

Creates a new asset in the portfolio.

```
POST /assets/
```

**Request Body:** `AssetCreate`

**Example Request:**

```json
{
  "name": "Apple Inc.",
  "symbol": "AAPL",
  "type": "stock",
  "quantity": 10,
  "purchase_price": 150.0,
  "purchase_currency": "USD",
  "notes": "Long-term investment"
}
```

**Response Schema:** `AssetRead`

**Cache Behavior:**

- This endpoint does not use cache
- May trigger cache updates for the new asset's price data

**Error Responses:**

- `400 Bad Request` - Invalid asset data
- `500 Internal Server Error` - Database operation failure

### Get All Assets

Retrieves all assets in the portfolio.

```
GET /assets/
```

**Response Schema:** List of `AssetRead`

**Cache Behavior:**

- This endpoint does not use cache for asset data
- May include cached price data in the response

**Error Responses:**

- `500 Internal Server Error` - Database operation failure

### Update Asset

Updates an existing asset.

```
PUT /assets/{asset_id}
```

**Path Parameters:**

- `asset_id` (required): ID of the asset to update

**Request Body:** `AssetUpdate`

**Response Schema:** `AssetRead`

**Cache Behavior:**

- This endpoint does not use cache
- May invalidate related price cache entries if asset symbol changes

**Error Responses:**

- `400 Bad Request` - Invalid asset data
- `404 Not Found` - Asset not found
- `500 Internal Server Error` - Database operation failure

### Delete Asset

Deletes an asset from the portfolio.

```
DELETE /assets/{asset_id}
```

**Path Parameters:**

- `asset_id` (required): ID of the asset to delete

**Response Schema:** `AssetRead`

**Cache Behavior:**

- This endpoint does not use cache
- May remove related price cache entries

**Error Responses:**

- `404 Not Found` - Asset not found
- `500 Internal Server Error` - Database operation failure

## Performance Monitoring Endpoints

### Get Performance Metrics

Retrieves performance monitoring metrics.

```
GET /performance/metrics
```

**Query Parameters:**

- `include_slow` (optional): Include slow operation details (default: false)

**Response:**

```json
{
  "api_calls": {
    "total": 150,
    "success_rate": 0.98,
    "average_response_time_ms": 245
  },
  "cache": {
    "hit_rate": 0.85,
    "miss_rate": 0.15,
    "average_lookup_time_ms": 5
  },
  "slow_operations": [
    {
      "endpoint": "/crypto/BTC",
      "duration_ms": 1250,
      "timestamp": "2025-07-19T09:45:30Z"
    }
  ]
}
```

**Cache Behavior:**

- This endpoint does not use cache
- Returns statistics about cache performance

**Error Responses:**

- `500 Internal Server Error` - Metrics collection failure

### Reset Performance Metrics

Resets all performance monitoring metrics.

```
POST /performance/metrics/reset
```

**Response:**

```json
{
  "status": "success",
  "message": "Performance metrics reset successfully"
}
```

**Cache Behavior:**

- This endpoint does not use cache
- Does not affect cache data

**Error Responses:**

- `500 Internal Server Error` - Metrics reset failure

## Health Check Endpoints

### General Health Check

Checks the overall health of the application.

```
GET /health
```

**Response:**

```json
{
  "status": "healthy",
  "version": "1.2.3",
  "uptime": "3d 5h 12m",
  "components": {
    "database": "healthy",
    "external_apis": "degraded",
    "cache": "healthy"
  }
}
```

**Cache Behavior:**

- This endpoint does not use cache
- Includes cache health status in the response

**Error Responses:**

- `503 Service Unavailable` - Critical service failure

### Database Health Check

Checks the health of the database connection.

```
GET /health/database
```

**Response:**

```json
{
  "status": "healthy",
  "connection_pool": {
    "active": 3,
    "idle": 7,
    "max": 20
  },
  "response_time_ms": 15
}
```

**Cache Behavior:**

- This endpoint does not use cache

**Error Responses:**

- `503 Service Unavailable` - Database connection failure

### External APIs Health Check

Checks the health of external API connections.

```
GET /health/external-apis
```

**Response:**

```json
{
  "status": "degraded",
  "apis": {
    "finnhub": {
      "status": "healthy",
      "response_time_ms": 350
    },
    "coingecko": {
      "status": "degraded",
      "response_time_ms": 1250,
      "error": "Slow response time"
    }
  }
}
```

**Cache Behavior:**

- This endpoint does not use cache
- May use cached API status information to reduce external calls

**Error Responses:**

- `503 Service Unavailable` - All external APIs unavailable

## Error Handling

All API endpoints follow consistent error handling patterns:

### Standard Error Response Format

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "additional": "error details",
      "field_errors": [
        {
          "field": "field_name",
          "error": "specific error for this field"
        }
      ]
    }
  }
}
```

### Common Error Codes

- `400 Bad Request` - Invalid input parameters
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server-side error
- `503 Service Unavailable` - Service temporarily unavailable

### Rate Limiting

The API implements rate limiting to protect external API quotas:

- Headers included in responses:
  - `X-RateLimit-Limit`: Maximum requests per time window
  - `X-RateLimit-Remaining`: Remaining requests in current window
  - `X-RateLimit-Reset`: Time when the rate limit resets (Unix timestamp)

## Cache Behavior

### Cache TTL Settings

Cache Time-To-Live (TTL) settings are configurable via environment variables:

- `PRICE_CACHE_TTL_MINUTES`: TTL for price data (default: 15 minutes)
- `CONVERSION_CACHE_TTL_HOURS`: TTL for conversion rates (default: 24 hours)

### Cache Status Indicators

All endpoints that return cached data include these fields:

- `cached`: Boolean indicating if the data came from cache
- `cache_age`: Age of the cached data in appropriate units (minutes or hours)

### Force Refresh Behavior

Endpoints that support the `force_refresh` parameter:

- When `force_refresh=true`, the system bypasses cache and fetches fresh data
- The cache is updated with the new data
- If the external API call fails, the system falls back to cached data if available

### Cache Invalidation

Cache entries are invalidated in these scenarios:

1. TTL expiration
2. Explicit cache clearing via API endpoints
3. Related data updates (e.g., asset symbol change)
