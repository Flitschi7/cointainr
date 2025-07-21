# Cointainr Deployment Scenarios

This document provides examples of environment configurations for different deployment scenarios.

## Local Development

### Backend (.env)

```
# Database Configuration
DATABASE_URL="sqlite+aiosqlite:///./cointainr.db"

# API Keys
FINNHUB_API_KEY="your_finnhub_api_key"
EXCHANGERATE_API_KEY="your_exchangerate_api_key"

# Cache Configuration
PRICE_CACHE_TTL_MINUTES=5
CONVERSION_CACHE_TTL_HOURS=1

# Application Settings
DEFAULT_CURRENCY=USD
FORCE_REFRESH_ONLY=false

# Logging Configuration
LOG_LEVEL=DEBUG
ENABLE_JSON_LOGGING=false
```

### Frontend (frontend/.env)

```
# API Configuration
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1

# Cache Configuration
VITE_PRICE_CACHE_TTL_MINUTES=5
VITE_CONVERSION_CACHE_TTL_HOURS=1

# Application Settings
VITE_DEFAULT_CURRENCY=USD
VITE_FORCE_REFRESH_ONLY=false
```

## Production Deployment

### Backend (.env)

```
# Database Configuration
DATABASE_URL="sqlite+aiosqlite:///./data/cointainr.db"

# API Keys
FINNHUB_API_KEY="your_finnhub_api_key"
EXCHANGERATE_API_KEY="your_exchangerate_api_key"

# Cache Configuration
PRICE_CACHE_TTL_MINUTES=15
CONVERSION_CACHE_TTL_HOURS=24
PRICE_CACHE_CLEANUP_DAYS=30
CONVERSION_CACHE_CLEANUP_DAYS=7

# Application Settings
DEFAULT_CURRENCY=USD
FORCE_REFRESH_ONLY=false

# Logging Configuration
LOG_LEVEL=INFO
ENABLE_JSON_LOGGING=true
LOG_FILE=/var/log/cointainr.log
```

### Frontend (frontend/.env)

```
# API Configuration
VITE_API_BASE_URL=https://your-domain.com/api/v1

# Cache Configuration
VITE_PRICE_CACHE_TTL_MINUTES=15
VITE_CONVERSION_CACHE_TTL_HOURS=24

# Application Settings
VITE_DEFAULT_CURRENCY=USD
VITE_FORCE_REFRESH_ONLY=false
```

## Limited API Quota Scenario

If you have limited API quota or want to minimize external API calls:

### Backend (.env)

```
# Database Configuration
DATABASE_URL="sqlite+aiosqlite:///./cointainr.db"

# API Keys
FINNHUB_API_KEY="your_finnhub_api_key"
EXCHANGERATE_API_KEY="your_exchangerate_api_key"

# Cache Configuration
PRICE_CACHE_TTL_MINUTES=60
CONVERSION_CACHE_TTL_HOURS=48
PRICE_CACHE_CLEANUP_DAYS=60
CONVERSION_CACHE_CLEANUP_DAYS=14

# Application Settings
DEFAULT_CURRENCY=USD
FORCE_REFRESH_ONLY=false

# Logging Configuration
LOG_LEVEL=INFO
ENABLE_JSON_LOGGING=false
```

### Frontend (frontend/.env)

```
# API Configuration
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1

# Cache Configuration
VITE_PRICE_CACHE_TTL_MINUTES=60
VITE_CONVERSION_CACHE_TTL_HOURS=48

# Application Settings
VITE_DEFAULT_CURRENCY=USD
VITE_FORCE_REFRESH_ONLY=false
```

## Docker Deployment

For Docker deployment, you can use environment variables in your docker-compose.yml file:

```yaml
version: "3"
services:
  cointainr:
    image: cointainr:latest
    ports:
      - "8000:8000"
      - "5173:5173"
    volumes:
      - ./data:/app/data
    environment:
      # Database Configuration
      - DATABASE_URL=sqlite+aiosqlite:///./data/cointainr.db

      # API Keys
      - FINNHUB_API_KEY=your_finnhub_api_key
      - EXCHANGERATE_API_KEY=your_exchangerate_api_key

      # Cache Configuration
      - PRICE_CACHE_TTL_MINUTES=15
      - CONVERSION_CACHE_TTL_HOURS=24
      - PRICE_CACHE_CLEANUP_DAYS=30
      - CONVERSION_CACHE_CLEANUP_DAYS=7

      # Application Settings
      - DEFAULT_CURRENCY=USD
      - FORCE_REFRESH_ONLY=false

      # Logging Configuration
      - LOG_LEVEL=INFO
      - ENABLE_JSON_LOGGING=false

      # Frontend Environment Variables
      - VITE_API_BASE_URL=http://localhost:8000/api/v1
      - VITE_PRICE_CACHE_TTL_MINUTES=15
      - VITE_CONVERSION_CACHE_TTL_HOURS=24
      - VITE_DEFAULT_CURRENCY=USD
      - VITE_FORCE_REFRESH_ONLY=false
```

## Testing Environment

For testing, you might want to disable caching entirely:

### Backend (.env)

```
# Database Configuration
DATABASE_URL="sqlite+aiosqlite:///:memory:"

# API Keys
FINNHUB_API_KEY="test_key"
EXCHANGERATE_API_KEY="test_key"

# Cache Configuration
PRICE_CACHE_TTL_MINUTES=0
CONVERSION_CACHE_TTL_HOURS=0

# Application Settings
DEFAULT_CURRENCY=USD
FORCE_REFRESH_ONLY=true

# Logging Configuration
LOG_LEVEL=DEBUG
ENABLE_JSON_LOGGING=false
```

### Frontend (frontend/.env)

```
# API Configuration
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1

# Cache Configuration
VITE_PRICE_CACHE_TTL_MINUTES=0
VITE_CONVERSION_CACHE_TTL_HOURS=0

# Application Settings
VITE_DEFAULT_CURRENCY=USD
VITE_FORCE_REFRESH_ONLY=true
```
