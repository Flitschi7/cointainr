# Cointainr Configuration Guide for Users

This guide explains how to configure Cointainr to suit your needs, focusing on cache settings and performance optimization.

## Cache Settings

Cointainr uses caching to reduce API calls and improve performance. You can customize these settings to balance data freshness with API usage.

### Price Cache

Price data is cached to reduce API calls to external services like Finnhub and CoinGecko.

- **Setting**: `PRICE_CACHE_TTL_MINUTES` (Backend) or `VITE_PRICE_CACHE_TTL_MINUTES` (Frontend)
- **Default**: 15 minutes
- **Recommendation**:
  - For real-time trading: 5-10 minutes
  - For casual portfolio tracking: 15-30 minutes
  - For minimal API usage: 60 minutes

### Conversion Cache

Currency conversion rates are cached to reduce API calls to exchange rate services.

- **Setting**: `CONVERSION_CACHE_TTL_HOURS` (Backend) or `VITE_CONVERSION_CACHE_TTL_HOURS` (Frontend)
- **Default**: 24 hours
- **Recommendation**:
  - For frequent currency changes: 6-12 hours
  - For standard usage: 24 hours
  - For minimal API usage: 48 hours

## Default Currency

You can set your preferred default currency for the application.

- **Setting**: `DEFAULT_CURRENCY` (Backend) or `VITE_DEFAULT_CURRENCY` (Frontend)
- **Default**: USD
- **Options**: Any valid three-letter currency code (e.g., EUR, GBP, JPY)

## Force Refresh Only Mode

This setting determines whether the application always bypasses the cache and fetches fresh data.

- **Setting**: `FORCE_REFRESH_ONLY` (Backend) or `VITE_FORCE_REFRESH_ONLY` (Frontend)
- **Default**: false
- **Options**:
  - `true`: Always fetch fresh data (uses more API calls)
  - `false`: Use cached data when available (recommended)

## How to Apply Settings

### Using .env Files

1. Create or edit the `.env` file in the project root directory for backend settings
2. Create or edit the `.env` file in the `frontend` directory for frontend settings
3. Add or modify the settings as needed
4. Restart the application for changes to take effect

Example backend `.env` file:

```
PRICE_CACHE_TTL_MINUTES=30
CONVERSION_CACHE_TTL_HOURS=12
DEFAULT_CURRENCY=EUR
FORCE_REFRESH_ONLY=false
```

Example frontend `.env` file:

```
VITE_PRICE_CACHE_TTL_MINUTES=30
VITE_CONVERSION_CACHE_TTL_HOURS=12
VITE_DEFAULT_CURRENCY=EUR
VITE_FORCE_REFRESH_ONLY=false
```

### Using Docker Environment Variables

If you're running Cointainr with Docker, you can set environment variables in your docker-compose.yml file or docker run command.

Example docker-compose.yml:

```yaml
version: "3"
services:
  cointainr:
    image: cointainr:latest
    environment:
      - PRICE_CACHE_TTL_MINUTES=30
      - CONVERSION_CACHE_TTL_HOURS=12
      - DEFAULT_CURRENCY=EUR
      - FORCE_REFRESH_ONLY=false
```

## Cache Indicators

Cointainr displays cache status indicators in the UI:

- **Green**: Fresh cached data
- **Yellow**: Cached data approaching expiration
- **Red**: Stale cached data (beyond TTL)

You can manually refresh data using the "Force Refresh" button regardless of cache status.

## Optimizing for Your Use Case

### High-Frequency Updates

If you want near real-time data:

```
PRICE_CACHE_TTL_MINUTES=5
CONVERSION_CACHE_TTL_HOURS=6
```

### Balanced Approach

For a good balance between freshness and API usage:

```
PRICE_CACHE_TTL_MINUTES=15
CONVERSION_CACHE_TTL_HOURS=24
```

### Minimal API Usage

If you want to minimize API calls:

```
PRICE_CACHE_TTL_MINUTES=60
CONVERSION_CACHE_TTL_HOURS=48
```

## Troubleshooting

### Cache Not Working

If the cache doesn't seem to be working:

1. Check that `FORCE_REFRESH_ONLY` is set to `false`
2. Verify that the application has been restarted after changing settings
3. Check the cache status indicators in the UI

### API Rate Limit Errors

If you're seeing API rate limit errors:

1. Increase the cache TTL values
2. Ensure `FORCE_REFRESH_ONLY` is set to `false`
3. Stagger your portfolio updates instead of refreshing everything at once
