# Cointainr Environment Configuration

This directory contains documentation for configuring Cointainr using environment variables.

## Available Documentation

- [Environment Configuration Guide](./environment_configuration.md) - Detailed technical documentation of all environment variables
- [User Configuration Guide](./user_configuration_guide.md) - User-friendly guide for configuring cache settings

## Quick Start

1. Copy `.env.example` to `.env` in the project root for backend settings
2. Copy `frontend/.env.example` to `frontend/.env` for frontend settings
3. Adjust values as needed
4. Restart the application

## Key Environment Variables

### Backend

- `PRICE_CACHE_TTL_MINUTES` - Time-to-live for price cache in minutes
- `CONVERSION_CACHE_TTL_HOURS` - Time-to-live for conversion cache in hours
- `DEFAULT_CURRENCY` - Default currency for display
- `FORCE_REFRESH_ONLY` - Always bypass cache when true

### Frontend

- `VITE_PRICE_CACHE_TTL_MINUTES` - Time-to-live for price cache in minutes
- `VITE_CONVERSION_CACHE_TTL_HOURS` - Time-to-live for conversion cache in hours
- `VITE_DEFAULT_CURRENCY` - Default currency for display
- `VITE_FORCE_REFRESH_ONLY` - Always bypass cache when true

## Docker Deployment

See the `docker-compose.yml` file in the project root for an example of setting environment variables with Docker.
