"""
Utilities for graceful degradation of external API failures.

This module provides functions for handling external API failures
with graceful degradation strategies.
"""

import logging
import time
from typing import Dict, Any, Optional, Callable, TypeVar, Awaitable
from datetime import datetime, timezone, timedelta
from functools import wraps

# Set up logger
logger = logging.getLogger(__name__)

# Type variables for generic functions
T = TypeVar("T")


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for external API calls.

    This class implements the circuit breaker pattern to prevent
    repeated calls to failing external APIs.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        reset_timeout: int = 60,
        half_open_timeout: int = 30,
    ):
        """
        Initialize the circuit breaker.

        Args:
            name: Name of the circuit breaker
            failure_threshold: Number of failures before opening the circuit
            reset_timeout: Time in seconds before resetting the circuit
            half_open_timeout: Time in seconds before trying a half-open state
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.half_open_timeout = half_open_timeout

        # Circuit state
        self.failures = 0
        self.state = "closed"  # closed, open, half-open
        self.last_failure_time = None
        self.last_success_time = None

    def record_success(self):
        """Record a successful API call."""
        self.failures = 0
        self.state = "closed"
        self.last_success_time = datetime.now(timezone.utc)

    def record_failure(self):
        """Record a failed API call."""
        self.failures += 1
        self.last_failure_time = datetime.now(timezone.utc)

        # Check if we should open the circuit
        if self.failures >= self.failure_threshold:
            self.state = "open"
            logger.warning(
                f"Circuit breaker '{self.name}' opened after {self.failures} failures"
            )

    def allow_request(self) -> bool:
        """
        Check if a request should be allowed.

        Returns:
            True if the request should be allowed, False otherwise
        """
        # If circuit is closed, allow the request
        if self.state == "closed":
            return True

        # If circuit is open, check if we should try a half-open state
        if self.state == "open":
            # Check if reset timeout has passed
            if self.last_failure_time is None:
                return True

            time_since_failure = (
                datetime.now(timezone.utc) - self.last_failure_time
            ).total_seconds()

            if time_since_failure >= self.reset_timeout:
                # Reset timeout has passed, try a half-open state
                self.state = "half-open"
                logger.info(
                    f"Circuit breaker '{self.name}' entering half-open state after {time_since_failure:.2f}s"
                )
                return True

            # Reset timeout has not passed, keep circuit open
            return False

        # If circuit is half-open, allow one request
        if self.state == "half-open":
            # Check if half-open timeout has passed since last attempt
            if self.last_failure_time is None:
                return True

            time_since_failure = (
                datetime.now(timezone.utc) - self.last_failure_time
            ).total_seconds()

            if time_since_failure >= self.half_open_timeout:
                # Half-open timeout has passed, allow one request
                logger.info(
                    f"Circuit breaker '{self.name}' allowing test request after {time_since_failure:.2f}s in half-open state"
                )
                return True

            # Half-open timeout has not passed, keep circuit open
            return False

        # Unknown state, allow the request
        return True

    def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the circuit breaker.

        Returns:
            Dict with circuit breaker status information
        """
        return {
            "name": self.name,
            "state": self.state,
            "failures": self.failures,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": (
                self.last_failure_time.isoformat() if self.last_failure_time else None
            ),
            "last_success_time": (
                self.last_success_time.isoformat() if self.last_success_time else None
            ),
        }


# Global registry of circuit breakers
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str) -> CircuitBreaker:
    """
    Get or create a circuit breaker.

    Args:
        name: Name of the circuit breaker

    Returns:
        CircuitBreaker instance
    """
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name)

    return _circuit_breakers[name]


def with_circuit_breaker(
    name: str,
    fallback_func: Optional[Callable[..., Awaitable[T]]] = None,
):
    """
    Decorator for applying circuit breaker pattern to async functions.

    Args:
        name: Name of the circuit breaker
        fallback_func: Async function to call if circuit is open

    Returns:
        Decorated function with circuit breaker
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get or create circuit breaker
            circuit_breaker = get_circuit_breaker(name)

            # Check if request should be allowed
            if not circuit_breaker.allow_request():
                logger.warning(f"Circuit breaker '{name}' is open, request blocked")

                # If fallback function is provided, call it
                if fallback_func:
                    return await fallback_func(*args, **kwargs)

                # No fallback, raise exception
                raise Exception(f"Circuit breaker '{name}' is open, request blocked")

            try:
                # Call the original function
                result = await func(*args, **kwargs)

                # Record success
                circuit_breaker.record_success()

                return result
            except Exception as e:
                # Record failure
                circuit_breaker.record_failure()

                # Re-raise the exception
                raise

        return wrapper

    return decorator


def get_all_circuit_breakers() -> Dict[str, Dict[str, Any]]:
    """
    Get status of all circuit breakers.

    Returns:
        Dict with circuit breaker status information
    """
    return {name: cb.get_status() for name, cb in _circuit_breakers.items()}
