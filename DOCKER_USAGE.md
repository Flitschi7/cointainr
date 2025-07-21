# Docker Usage Guide

## 🚀 Quick Start

### 1. Download docker-compose.yml

```bash
curl -O https://raw.githubusercontent.com/yourusername/cointainr/main/docker-compose.yml
```

### 2. Edit API Keys

Open `docker-compose.yml` and replace these lines with your actual API keys:

```yaml
- FINNHUB_API_KEY=your_finnhub_api_key_here
- EXCHANGERATE_API_KEY=your_exchangerate_api_key_here
```

### 3. Start the Application

```bash
docker-compose up -d
```

### 4. Access the Application

- **Frontend + Backend**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🔧 Configuration

All configuration is now done directly in `docker-compose.yml`. Key settings:

```yaml
# API Keys (Required)
- FINNHUB_API_KEY=your_actual_key_here
- EXCHANGERATE_API_KEY=your_actual_key_here

# Cache Settings
- PRICE_CACHE_TTL_MINUTES=15 # How long to cache prices
- CONVERSION_CACHE_TTL_HOURS=8 # How long to cache currency rates

# Application Settings
- DEFAULT_CURRENCY=EUR # Your preferred currency
- FORCE_REFRESH_ONLY=false # Auto-refresh vs manual only
```

## 📊 Management Commands

```bash
# Start the application
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the application
docker-compose down

# Update to latest image
docker-compose pull
docker-compose up -d

# Restart the application
docker-compose restart
```

## 💾 Data Persistence

Your data is stored in the `./data` directory and will persist between container restarts.

## 🔑 Getting API Keys

1. **Finnhub API Key**: https://finnhub.io/
2. **ExchangeRate API Key**: https://exchangerate-api.com/

Both offer free tiers that work great for personal use!
