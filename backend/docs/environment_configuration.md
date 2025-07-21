# Cointainr Environment Configuration Guide

This document provides detailed information about the environment variables used in Cointainr for both backend and frontend components.

## Overview

Cointainr uses environment variables to configure various aspects of the application, including:

- Cache behavior and TTL settings
- Default currency preferences
- API keys for external services
- Database connection settings
- Logging configuration

## Backend Environment Variables

### Core Configuration

| Variable               | Description                       | Default                              | Example                                    |
| ---------------------- | --------------------------------- | ------------------------------------ | ------------------------------------------ |
| `DATABASE_URL`         | SQLite database connection string | `sqlite+aiosqlite:///./cointainr.db` | `sqlite+aiosqlite:///./data/cointainr.db`  |
| `FINNHUB_API_KEY`      | API key for Finnhub stock data    | -                                    | `cq5u1r9r01qlbj4vhdtgcq5u1r9r01qlbj4vhdu0` |
| `EXCHANGERATE_API_KEY` | API key for ExchangeRate API      | -                                    | `ebad7f9e6f836697346481b2`                 |

### Cache Configuration

| Variable                        | Description                                          | Default | Example |
| ------------------------------- | ---------------------------------------------------- | ------- | ------- |
| `PRICE_CACHE_TTL_MINUTES`       | Time-to-live for price cache in minutes              | `15`    | `30`    |
| `CONVERSION_CACHE_TTL_HOURS`    | Time-to-live for conversion cache in hours           | `24`    | `12`    |
| `PRICE_CACHE_CLEANUP_DAYS`      | Days to keep price cache entries before cleanup      | `30`    | `15`    |
| `CONVERSION_CACHE_CLEANUP_DAYS` | Days to keep conversion cache entries before cleanup | `7`     | `14`    |

### Application Settings

| Variable             | Description                   | Default | Example |
| -------------------- | ----------------------------- | ------- | ------- |
| `DEFAULT_CURRENCY`   | Default currency for display  | `USD`   | `EUR`   |
| `FORCE_REFRESH_ONLY` | Always bypass cache when true | `false` | `true`  |

### Logging Configuration

| Variable              | Description                 | Default | Example                  |
| --------------------- | --------------------------- | ------- | ------------------------ |
| `LOG_LEVEL`           | Logging level               | `INFO`  | `DEBUG`                  |
| `ENABLE_JSON_LOGGING` | Enable JSON format for logs | `false` | `true`                   |
| `LOG_FILE`            | Path to log file (optional) | -       | `/var/log/cointainr.log` |

## Frontend Environment Variables

Frontend environment variables are prefixed with `VITE_` to make them accessible in the client-side code.

| Variable                          | Description                                | Default                        | Example                          |
| --------------------------------- | ------------------------------------------ | ------------------------------ | -------------------------------- |
| `VITE_API_BASE_URL`               | Base URL for the backend API               | `http://127.0.0.1:8000/api/v1` | `https://api.example.com/api/v1` |
| `VITE_PRICE_CACHE_TTL_MINUTES`    | Time-to-live for price cache in minutes    | `15`                           | `30`                             |
| `VITE_CONVERSION_CACHE_TTL_HOURS` | Time-to-live for conversion cache in hours | `24`                           | `12`                             |
| `VITE_DEFAULT_CURRENCY`           | Default currency for display               | `USD`                          | `EUR`                            |
| `VITE_FORCE_REFRESH_ONLY`         | Always bypass cache when true              | `false`                        | `true`                           |

## Deployment Scenarios

### Development Environment

For local development, create a `.env` file in the project root with the following settings:

```
DATABASE_URL="sqlite+aiosqlite:///./cointainr.db"
FINNHUB_API_KEY="your_finnhub_api_key"
EXCHANGERATE_API_KEY="your_exchangerate_api_key"
PRICE_CACHE_TTL_MINUTES=5
CONVERSION_CACHE_TTL_HOURS=1
LOG_LEVEL=DEBUG
```

And a `.env` file in the `frontend` directory:

```
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
VITE_PRICE_CACHE_TTL_MINUTES=5
VITE_CONVERSION_CACHE_TTL_HOURS=1
```

### Production Environment

For production deployment, consider the following settings:

```
DATABASE_URL="sqlite+aiosqlite:///./data/cointainr.db"
FINNHUB_API_KEY="your_finnhub_api_key"
EXCHANGERATE_API_KEY="your_exchangerate_api_key"
PRICE_CACHE_TTL_MINUTES=15
CONVERSION_CACHE_TTL_HOURS=24
LOG_LEVEL=INFO
ENABLE_JSON_LOGGING=true
LOG_FILE=/var/log/cointainr.log
```

And for the frontend:

```
VITE_API_BASE_URL=https://api.example.com/api/v1
VITE_PRICE_CACHE_TTL_MINUTES=15
VITE_CONVERSION_CACHE_TTL_HOURS=24
```

### Low API Usage Scenario

If you have limited API quota, consider these settings:

```
PRICE_CACHE_TTL_MINUTES=60
CONVERSION_CACHE_TTL_HOURS=48
FORCE_REFRESH_ONLY=false
```

And for the frontend:

```
VITE_PRICE_CACHE_TTL_MINUTES=60
VITE_CONVERSION_CACHE_TTL_HOURS=48
VITE_FORCE_REFRESH_ONLY=false
```

## Docker Environment Variables

When running Cointainr with Docker, you can pass environment variables using:

1. Docker Compose:

```yaml
version: "3"
services:
  cointainr:
    image: cointainr:latest
    environment:
      - DATABASE_URL=sqlite+aiosqlite:///./data/cointainr.db
      - FINNHUB_API_KEY=your_finnhub_api_key
      - EXCHANGERATE_API_KEY=your_exchangerate_api_key
      - PRICE_CACHE_TTL_MINUTES=15
      - CONVERSION_CACHE_TTL_HOURS=24
      - DEFAULT_CURRENCY=USD
    volumes:
      - ./data:/app/data
    ports:
      - "8000:8000"
      - "5173:5173"
```

2. Docker Run Command:

```bash
docker run -d \
  -e DATABASE_URL=sqlite+aiosqlite:///./data/cointainr.db \
  -e FINNHUB_API_KEY=your_finnhub_api_key \
  -e EXCHANGERATE_API_KEY=your_exchangerate_api_key \
  -e PRICE_CACHE_TTL_MINUTES=15 \
  -e CONVERSION_CACHE_TTL_HOURS=24 \
  -e DEFAULT_CURRENCY=USD \
  -v ./data:/app/data \
  -p 8000:8000 -p 5173:5173 \
  cointainr:latest
```

## Troubleshooting

### Cache Not Working Correctly

If the cache doesn't seem to be working as expected:

1. Check that `FORCE_REFRESH_ONLY` is set to `false`
2. Verify that the TTL values are set appropriately
3. Check the logs for any cache-related errors

### API Rate Limit Issues

If you're experiencing API rate limit issues:

1. Increase the cache TTL values
2. Set `FORCE_REFRESH_ONLY` to `false`
3. Consider implementing a staggered refresh strategy

### Environment Variables Not Applied

If environment variables don't seem to be applied:

1. Make sure the `.env` file is in the correct location
2. Restart the application after changing environment variables
3. Check that variable names are spelled correctly
