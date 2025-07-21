# Cointainr Error Handling System

This document describes the error handling system used in the Cointainr backend.

## Overview

The Cointainr error handling system provides:

1. **Standardized Error Responses**: Consistent error format across all API endpoints
2. **Detailed Error Logging**: Structured logging with context for debugging
3. **Graceful Degradation**: Fallback mechanisms for external API failures
4. **Request Tracking**: Request IDs for tracing errors across the system
5. **Circuit Breaker Pattern**: Protection against cascading failures

## Error Response Format

All API errors follow this standardized format:

```json
{
  "error": true,
  "message": "Human-readable error message",
  "category": "error_category",
  "status_code": 500,
  "timestamp": "2023-07-19T12:34:56.789Z",
  "request_id": "unique-request-id",
  "details": {
    "additional": "error details"
  }
}
```

## Error Categories

Errors are categorized for better handling and reporting:

- `validation_error`: Input validation failures
- `database_error`: Database operation failures
- `external_api_error`: External API call failures
- `authentication_error`: Authentication failures
- `authorization_error`: Authorization failures
- `rate_limit_error`: Rate limit exceeded
- `not_found_error`: Resource not found
- `cache_error`: Cache operation failures
- `internal_error`: Internal server errors
- `unknown_error`: Uncategorized errors

## Graceful Degradation

The system implements several strategies for graceful degradation:

### 1. Cache Fallback

When external API calls fail, the system attempts to use cached data:

```python
try:
    # Try to get fresh data from API
    data = await api_service.get_data()
except ExternalAPIError:
    # Fall back to cached data
    data = await cache_service.get_cached_data()
    data["cached"] = True
```

### 2. Circuit Breaker Pattern

The circuit breaker pattern prevents repeated calls to failing external APIs:

```python
@with_circuit_breaker(name="api_name")
async def call_external_api():
    # This function won't be called if the circuit is open
    return await external_api_call()
```

### 3. Retry with Exponential Backoff

For transient failures, the system implements retry with exponential backoff:

```python
# Retry up to 3 times with exponential backoff
result = await retry_with_exponential_backoff(
    func=api_call,
    max_retries=3
)
```

## Request Tracking

All requests are assigned a unique request ID for tracking:

1. The request ID is added to all log messages
2. The request ID is included in error responses
3. The request ID is added to response headers as `X-Request-ID`

## Logging

The system uses structured logging with JSON format:

```json
{
  "timestamp": "2023-07-19T12:34:56.789Z",
  "level": "ERROR",
  "logger": "app.services.api",
  "message": "API call failed",
  "module": "api_service",
  "function": "get_data",
  "line": 42,
  "request_id": "unique-request-id",
  "exception": {
    "type": "HTTPError",
    "message": "404 Not Found",
    "traceback": "..."
  }
}
```

## Health Checks

The system provides health check endpoints for monitoring:

- `/api/v1/health`: Overall system health
- `/api/v1/health/database`: Database health
- `/api/v1/health/external-apis`: External APIs health
- `/api/v1/health/circuit-breakers`: Circuit breaker status

## Best Practices

When adding new endpoints or services:

1. Use the `StandardError` classes for consistent error handling
2. Add appropriate error handling for all external API calls
3. Implement graceful degradation with cache fallback
4. Use the circuit breaker pattern for external dependencies
5. Include request IDs in all log messages
6. Return standardized error responses
