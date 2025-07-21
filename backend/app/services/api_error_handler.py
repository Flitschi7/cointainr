"""
API error handler service for external API calls.

This module provides utilities for handling errors from external API calls
with graceful degradation, cache fallback support, and retry logic.
"""

import logging
import asyncio
import random
from typing import Any, Dict, Optional, Callable, TypeVar, Awaitable, List
from functools import wraps
from datetime import datetime, timezone
import httpx
from app.core.error_handling import ExternalAPIError

# Set up logger
logger = logging.getLogger(__name__)

# Type variables for generic functions
T = TypeVar("T")

# Constants for retry logic
MAX_RETRIES = 3
BASE_DELAY = 1.0  # Base delay in seconds
MAX_DELAY = 10.0  # Maximum delay in seconds
JITTER = 0.1  # Jitter factor for randomization


class APIErrorContext:
    """Context for API error handling with detailed information."""

    def __init__(
        self,
        service_name: str,
        operation: str,
        request_info: Optional[Dict[str, Any]] = None,
        retry_count: int = 0,
        max_retries: int = MAX_RETRIES,
    ):
        """
        Initialize API error context.

        Args:
            service_name: Name of the external service
            operation: Operation being performed
            request_info: Information about the request
            retry_count: Current retry count
            max_retries: Maximum number of retries
        """
        self.service_name = service_name
        self.operation = operation
        self.request_info = request_info or {}
        self.retry_count = retry_count
        self.max_retries = max_retries
        self.start_time = datetime.now(timezone.utc)
        self.attempts = []
        self.last_error = None
        self.request_id = f"{service_name}-{operation}-{self.start_time.timestamp()}"

    def add_attempt(self, error: Exception, duration_ms: float):
        """
        Add an attempt to the context.

        Args:
            error: Error that occurred
            duration_ms: Duration of the attempt in milliseconds
        """
        self.attempts.append(
            {
                "attempt": len(self.attempts) + 1,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error_type": type(error).__name__,
                "error_message": str(error),
                "duration_ms": duration_ms,
            }
        )
        self.last_error = error

    def can_retry(self) -> bool:
        """
        Check if we can retry the operation.

        Returns:
            True if we can retry, False otherwise
        """
        return self.retry_count < self.max_retries

    def get_retry_delay(self) -> float:
        """
        Get the delay before the next retry with exponential backoff and jitter.

        Returns:
            Delay in seconds
        """
        # Calculate base delay with exponential backoff
        delay = min(BASE_DELAY * (2**self.retry_count), MAX_DELAY)

        # Add jitter to avoid thundering herd problem
        jitter_amount = delay * JITTER
        delay = delay + random.uniform(-jitter_amount, jitter_amount)

        return max(0.1, delay)  # Ensure minimum delay of 100ms

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert context to dictionary for logging and error details.

        Returns:
            Dictionary representation of the context
        """
        return {
            "service_name": self.service_name,
            "operation": self.operation,
            "request_info": self.request_info,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "start_time": self.start_time.isoformat(),
            "duration_ms": (
                datetime.now(timezone.utc) - self.start_time
            ).total_seconds()
            * 1000,
            "attempts": self.attempts,
            "request_id": self.request_id,
        }


async def handle_api_error(
    error: Exception,
    context: APIErrorContext,
    cache_fallback_func: Optional[Callable[[], Awaitable[T]]] = None,
) -> Dict[str, Any]:
    """
    Handle errors from external API calls with graceful degradation.

    Args:
        error: Original exception from the API call
        context: API error context
        cache_fallback_func: Async function to call for cache fallback data

    Returns:
        Error response dictionary with fallback data if available

    Raises:
        ExternalAPIError: If no fallback is available or allowed
    """
    # Log the error with structured context
    logger.error(
        f"External API error in {context.service_name}.{context.operation}: {str(error)}",
        extra={"api_error_context": context.to_dict()},
        exc_info=True,
    )

    # Prepare error details
    error_details = {
        "service": context.service_name,
        "operation": context.operation,
        "error_type": type(error).__name__,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": context.request_id,
        "attempts": len(context.attempts),
    }

    # Add rate limit information if available
    if isinstance(error, httpx.HTTPStatusError) and error.response.status_code == 429:
        retry_after = error.response.headers.get("Retry-After")
        if retry_after:
            try:
                error_details["retry_after"] = int(retry_after)
            except ValueError:
                # If Retry-After is a date string, we don't parse it here
                pass

    # Check if we can use cache fallback
    if cache_fallback_func:
        try:
            # Try to get fallback data from cache
            logger.info(
                f"Attempting to use cache fallback for {context.service_name}.{context.operation}",
                extra={"request_id": context.request_id},
            )
            fallback_data = await cache_fallback_func()

            if fallback_data:
                # Return response with fallback data and warning
                logger.info(
                    f"Successfully used cache fallback for {context.service_name}.{context.operation}",
                    extra={"request_id": context.request_id},
                )
                return {
                    **fallback_data,
                    "warning": f"{context.service_name} API error, using cached data",
                    "cache_fallback": True,
                    "error_details": error_details,
                    "request_id": context.request_id,
                }
        except Exception as fallback_error:
            # Log fallback error but continue with original error
            logger.error(
                f"Cache fallback failed for {context.service_name}.{context.operation}: {str(fallback_error)}",
                extra={"request_id": context.request_id},
                exc_info=True,
            )
            error_details["fallback_error"] = str(fallback_error)

    # Determine appropriate status code based on error type
    status_code = 502  # Default for external API errors

    if isinstance(error, httpx.HTTPStatusError):
        if error.response.status_code == 429:
            status_code = 429  # Rate limit exceeded
        elif error.response.status_code == 404:
            status_code = 404  # Resource not found
        else:
            status_code = error.response.status_code
    elif isinstance(error, httpx.TimeoutException):
        status_code = 504  # Gateway timeout
    elif isinstance(error, httpx.ConnectError):
        status_code = 503  # Service unavailable

    # No fallback available or fallback failed, raise standardized error
    raise ExternalAPIError(
        message=f"{context.service_name} API error: {str(error)}",
        status_code=status_code,
        details=error_details,
        original_error=error,
    )


async def retry_with_exponential_backoff(
    func: Callable[..., Awaitable[T]],
    context: APIErrorContext,
    *args,
    **kwargs,
) -> T:
    """
    Retry a function with exponential backoff.

    Args:
        func: Async function to retry
        context: API error context
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function

    Returns:
        Result of the function

    Raises:
        ExternalAPIError: If all retries fail
    """
    while True:
        start_time = datetime.now(timezone.utc)
        try:
            # Call the function
            result = await func(*args, **kwargs)

            # If successful after retries, log success
            if context.retry_count > 0:
                logger.info(
                    f"Successfully completed {context.service_name}.{context.operation} after {context.retry_count + 1} attempts",
                    extra={"request_id": context.request_id},
                )

            return result
        except Exception as error:
            # Calculate duration
            duration_ms = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds() * 1000

            # Add attempt to context
            context.add_attempt(error, duration_ms)

            # Check if we can retry
            if context.can_retry():
                # Increment retry count
                context.retry_count += 1

                # Calculate delay
                delay = context.get_retry_delay()

                # Log retry attempt
                logger.warning(
                    f"Retrying {context.service_name}.{context.operation} after error: {str(error)} "
                    f"(Attempt {context.retry_count}/{context.max_retries}, delay: {delay:.2f}s)",
                    extra={"request_id": context.request_id},
                )

                # Wait before retrying
                await asyncio.sleep(delay)
            else:
                # No more retries, handle the error
                return await handle_api_error(
                    error=error,
                    context=context,
                    cache_fallback_func=kwargs.get("cache_fallback_func"),
                )


def with_api_error_handling(
    service_name: str,
    operation: str,
    max_retries: int = MAX_RETRIES,
    retry_on_exceptions: Optional[List[type]] = None,
):
    """
    Decorator for handling API errors with graceful degradation and retry logic.

    Args:
        service_name: Name of the external service
        operation: Operation being performed
        max_retries: Maximum number of retries
        retry_on_exceptions: List of exception types to retry on (defaults to network errors)

    Returns:
        Decorated function with error handling and retry logic
    """
    # Default exceptions to retry on
    if retry_on_exceptions is None:
        retry_on_exceptions = [
            httpx.HTTPStatusError,  # HTTP errors (4xx, 5xx)
            httpx.TimeoutException,  # Timeouts
            httpx.ConnectError,  # Connection errors
            ConnectionError,  # General connection errors
            asyncio.TimeoutError,  # Async timeouts
        ]

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request info from kwargs for context
            request_info = {}
            for key, value in kwargs.items():
                if isinstance(value, (str, int, float, bool)) or value is None:
                    request_info[key] = value

            # Create error context
            context = APIErrorContext(
                service_name=service_name,
                operation=operation,
                request_info=request_info,
                max_retries=max_retries,
            )

            try:
                # Check if we should use retry logic
                should_retry = any(
                    issubclass(exc, Exception) for exc in retry_on_exceptions
                )

                if should_retry:
                    # Use retry logic
                    return await retry_with_exponential_backoff(
                        func=func,
                        context=context,
                        *args,
                        **kwargs,
                    )
                else:
                    # No retry, just call the function
                    return await func(*args, **kwargs)
            except Exception as error:
                # Check if we have a cache fallback option
                allow_expired = kwargs.get("allow_expired", False)
                force_refresh = kwargs.get("force_refresh", False)

                if allow_expired and not force_refresh:
                    # Create a cache fallback function that calls the original function
                    # with allow_expired=True and force_refresh=False
                    async def cache_fallback():
                        # Make a copy of kwargs to avoid modifying the original
                        fallback_kwargs = kwargs.copy()
                        fallback_kwargs["allow_expired"] = True
                        fallback_kwargs["force_refresh"] = False
                        return await func(*args, **fallback_kwargs)

                    # Handle the error with cache fallback
                    return await handle_api_error(
                        error=error,
                        context=context,
                        cache_fallback_func=cache_fallback,
                    )
                else:
                    # No cache fallback available, handle the error directly
                    return await handle_api_error(
                        error=error,
                        context=context,
                    )

        return wrapper

    return decorator
