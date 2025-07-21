# Error Response Documentation

This document provides detailed information about error responses in the Cointainr API, including standard formats, error codes, and handling strategies.

## Standard Error Response Format

All API endpoints return errors in a consistent format:

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

## HTTP Status Codes

| Status Code | Description           | Common Use Cases                            |
| ----------- | --------------------- | ------------------------------------------- |
| 400         | Bad Request           | Invalid input parameters, validation errors |
| 401         | Unauthorized          | Missing or invalid authentication           |
| 403         | Forbidden             | Insufficient permissions                    |
| 404         | Not Found             | Resource not found                          |
| 422         | Unprocessable Entity  | Request validation failed                   |
| 429         | Too Many Requests     | Rate limit exceeded                         |
| 500         | Internal Server Error | Unexpected server error                     |
| 503         | Service Unavailable   | Service temporarily unavailable             |

## Error Codes

### General Error Codes

| Error Code            | Description                  | HTTP Status |
| --------------------- | ---------------------------- | ----------- |
| `GENERAL_ERROR`       | Generic error                | 500         |
| `VALIDATION_ERROR`    | Input validation failed      | 400         |
| `RESOURCE_NOT_FOUND`  | Requested resource not found | 404         |
| `RATE_LIMIT_EXCEEDED` | API rate limit exceeded      | 429         |

### Cache-Specific Error Codes

| Error Code                | Description                  | HTTP Status |
| ------------------------- | ---------------------------- | ----------- |
| `CACHE_CLEAR_FAILED`      | Failed to clear cache        | 500         |
| `CACHE_UPDATE_FAILED`     | Failed to update cache       | 500         |
| `CACHE_STATS_UNAVAILABLE` | Cache statistics unavailable | 500         |

### Price API Error Codes

| Error Code           | Description                | HTTP Status |
| -------------------- | -------------------------- | ----------- |
| `PRICE_FETCH_FAILED` | Failed to fetch price data | 500         |
| `INVALID_SYMBOL`     | Invalid asset symbol       | 400         |
| `SYMBOL_NOT_FOUND`   | Asset symbol not found     | 404         |
| `EXTERNAL_API_ERROR` | External API error         | 503         |

### Conversion Error Codes

| Error Code           | Description                   | HTTP Status |
| -------------------- | ----------------------------- | ----------- |
| `CONVERSION_FAILED`  | Currency conversion failed    | 500         |
| `INVALID_CURRENCY`   | Invalid currency code         | 400         |
| `RATE_NOT_AVAILABLE` | Conversion rate not available | 404         |

### Asset Error Codes

| Error Code            | Description            | HTTP Status |
| --------------------- | ---------------------- | ----------- |
| `ASSET_CREATE_FAILED` | Failed to create asset | 500         |
| `ASSET_UPDATE_FAILED` | Failed to update asset | 500         |
| `ASSET_DELETE_FAILED` | Failed to delete asset | 500         |
| `ASSET_NOT_FOUND`     | Asset not found        | 404         |
| `DUPLICATE_ASSET`     | Asset already exists   | 400         |

## Field Validation Errors

For validation errors, the `field_errors` array contains specific errors for each field:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Input validation failed",
    "details": {
      "field_errors": [
        {
          "field": "symbol",
          "error": "Symbol must be 1-10 characters"
        },
        {
          "field": "quantity",
          "error": "Quantity must be greater than 0"
        }
      ]
    }
  }
}
```

## Rate Limiting Headers

When rate limits are enforced, these headers are included in responses:

| Header                  | Description                                      |
| ----------------------- | ------------------------------------------------ |
| `X-RateLimit-Limit`     | Maximum requests per time window                 |
| `X-RateLimit-Remaining` | Remaining requests in current window             |
| `X-RateLimit-Reset`     | Time when the rate limit resets (Unix timestamp) |

Example:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1626988800
```

## Error Handling Implementation

### Backend Error Handling

The backend uses a centralized error handling middleware:

```python
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Input validation failed",
                "details": {
                    "field_errors": [
                        {
                            "field": error["loc"][-1],
                            "error": error["msg"]
                        }
                        for error in exc.errors()
                    ]
                }
            }
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.detail.get("code", "HTTP_ERROR"),
                "message": exc.detail.get("message", str(exc.detail)),
                "details": exc.detail.get("details", {})
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    # Log the error
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "GENERAL_ERROR",
                "message": "An unexpected error occurred",
                "details": {
                    "type": type(exc).__name__
                }
            }
        }
    )
```

### Frontend Error Handling

The frontend uses a centralized error handling service:

```typescript
class ErrorHandler {
  /**
   * Handles API errors consistently
   */
  handleApiError(error: any): void {
    // Extract error details from response
    const errorDetails = this.extractErrorDetails(error);

    // Log the error
    console.error(`API Error: ${errorDetails.message}`, errorDetails);

    // Handle specific error types
    switch (errorDetails.code) {
      case "RATE_LIMIT_EXCEEDED":
        this.handleRateLimitError(errorDetails);
        break;
      case "EXTERNAL_API_ERROR":
        this.handleExternalApiError(errorDetails);
        break;
      default:
        this.handleGenericError(errorDetails);
    }
  }

  /**
   * Extracts structured error details from various error formats
   */
  private extractErrorDetails(error: any): ErrorDetails {
    // Default error structure
    const defaultError: ErrorDetails = {
      code: "UNKNOWN_ERROR",
      message: "An unknown error occurred",
      status: 500,
      details: {},
    };

    // No error object
    if (!error) {
      return defaultError;
    }

    // Axios error with response
    if (error.response && error.response.data && error.response.data.error) {
      const apiError = error.response.data.error;
      return {
        code: apiError.code || defaultError.code,
        message: apiError.message || defaultError.message,
        status: error.response.status,
        details: apiError.details || {},
      };
    }

    // Network error
    if (error.message && error.message.includes("Network Error")) {
      return {
        code: "NETWORK_ERROR",
        message: "Network connection error",
        status: 0,
        details: { original: error.message },
      };
    }

    // Generic error with message
    if (error.message) {
      return {
        code: error.code || defaultError.code,
        message: error.message,
        status: error.status || defaultError.status,
        details: error.details || {},
      };
    }

    return defaultError;
  }

  /**
   * Handles rate limit errors
   */
  private handleRateLimitError(error: ErrorDetails): void {
    // Show rate limit warning
    // Implement backoff strategy
  }

  /**
   * Handles external API errors
   */
  private handleExternalApiError(error: ErrorDetails): void {
    // Show degraded service warning
    // Fall back to cached data
  }

  /**
   * Handles generic errors
   */
  private handleGenericError(error: ErrorDetails): void {
    // Show generic error message
  }
}
```

## Graceful Degradation

The API implements graceful degradation for error scenarios:

### Cache Fallback

When external API calls fail, the system falls back to cached data:

```python
async def get_price_with_fallback(self, asset_id: str) -> PriceData:
    """Get price with fallback to cache on error."""
    try:
        # Try to get fresh data
        return await self._fetch_fresh_price(asset_id)
    except ExternalApiError as e:
        logger.warning(f"External API error: {str(e)}, falling back to cache")

        # Try to get cached data
        cache_entry = await self.cache_service.get_price_cache_entry(asset_id)
        if cache_entry:
            return PriceData(
                symbol=cache_entry.symbol,
                price=cache_entry.price,
                currency=cache_entry.currency,
                last_updated=cache_entry.timestamp,
                cached=True,
                cache_age=self._calculate_cache_age(cache_entry.timestamp),
                is_fallback=True
            )

        # No cache available, re-raise the error
        raise
```

### Retry Logic

For transient errors, the system implements retry logic with exponential backoff:

```python
@retry(
    retry=retry_if_exception_type(TransientError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    before_sleep=before_sleep_log(logger, logging.WARNING)
)
async def fetch_with_retry(self, url: str) -> Dict[str, Any]:
    """Fetch data with retry logic."""
    try:
        async with self.session.get(url, timeout=10) as response:
            if response.status == 429:
                # Rate limit exceeded
                retry_after = int(response.headers.get("Retry-After", "60"))
                raise RateLimitError(f"Rate limit exceeded, retry after {retry_after}s")

            if response.status >= 500:
                # Server error, may be transient
                raise TransientError(f"Server error: {response.status}")

            if response.status >= 400:
                # Client error, not transient
                raise ClientError(f"Client error: {response.status}")

            return await response.json()
    except asyncio.TimeoutError:
        raise TransientError("Request timed out")
    except aiohttp.ClientError as e:
        raise TransientError(f"Connection error: {str(e)}")
```

## Circuit Breaker Pattern

For external API calls, the system implements a circuit breaker pattern:

```python
class CircuitBreaker:
    def __init__(self, name: str, failure_threshold: int = 5, reset_timeout: int = 60):
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.state = "closed"  # closed, open, half-open
        self.last_failure_time = 0

    async def execute(self, func, *args, **kwargs):
        """Execute function with circuit breaker pattern."""
        # Check if circuit is open
        if self.state == "open":
            # Check if reset timeout has elapsed
            if time.time() - self.last_failure_time > self.reset_timeout:
                # Move to half-open state
                self.state = "half-open"
                logger.info(f"Circuit {self.name} changed from open to half-open")
            else:
                # Circuit is still open
                raise CircuitBreakerOpenError(f"Circuit {self.name} is open")

        try:
            # Execute the function
            result = await func(*args, **kwargs)

            # Success, reset failure count
            if self.state == "half-open":
                # Move back to closed state
                self.state = "closed"
                self.failures = 0
                logger.info(f"Circuit {self.name} changed from half-open to closed")

            return result
        except Exception as e:
            # Increment failure count
            self.failures += 1
            self.last_failure_time = time.time()

            # Check if failure threshold reached
            if self.failures >= self.failure_threshold:
                # Open the circuit
                self.state = "open"
                logger.warning(f"Circuit {self.name} opened after {self.failures} failures")

            # Re-raise the exception
            raise
```

## Monitoring and Alerting

The system includes monitoring for error patterns:

- Error rate tracking by endpoint and error type
- Alert thresholds for critical errors
- Dashboard for error visualization
- Log aggregation for error analysis
