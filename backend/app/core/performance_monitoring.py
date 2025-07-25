"""
Performance monitoring utilities for Cointainr.

This module provides functions and classes for monitoring application performance,
including API call tracking, cache hit/miss metrics, and slow operation logging.
"""

import time
import logging
import functools
import statistics
import asyncio
from typing import Dict, Any, Optional, Callable, TypeVar, cast
from datetime import datetime
from contextlib import contextmanager
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Set up logger
logger = logging.getLogger(__name__)

# Type variable for generic function decorator
F = TypeVar("F", bound=Callable[..., Any])

# Global performance metrics storage
_performance_metrics = {
    "api_calls": {
        "total": 0,
        "by_endpoint": {},
        "response_times": [],
        "slow_operations": [],
    },
    "cache": {
        "hits": 0,
        "misses": 0,
        "by_type": {
            "price": {"hits": 0, "misses": 0},
            "conversion": {"hits": 0, "misses": 0},
        },
    },
    "database": {
        "queries": 0,
        "slow_queries": [],
        "query_times": [],
    },
    "external_apis": {
        "calls": 0,
        "errors": 0,
        "by_service": {},
    },
}

# Configuration
_slow_threshold_ms = 500  # Threshold for slow operations in milliseconds
_max_metrics_history = 1000  # Maximum number of metrics to store in history


def configure_performance_monitoring(
    slow_threshold_ms: int = 500, max_metrics_history: int = 1000
) -> None:
    """
    Configure performance monitoring settings.

    Args:
        slow_threshold_ms: Threshold for slow operations in milliseconds
        max_metrics_history: Maximum number of metrics to store in history
    """
    global _slow_threshold_ms, _max_metrics_history
    _slow_threshold_ms = slow_threshold_ms
    _max_metrics_history = max_metrics_history
    logger.info(
        f"Performance monitoring configured: slow_threshold={slow_threshold_ms}ms, "
        f"max_history={max_metrics_history}"
    )


@contextmanager
def track_operation_time(operation_type: str, operation_name: str):
    """
    Context manager to track operation execution time.

    Args:
        operation_type: Type of operation (api, database, external_api)
        operation_name: Name of the specific operation

    Example:
        with track_operation_time('database', 'get_user_by_id'):
            user = await db.execute(select(User).where(User.id == user_id))
    """
    start_time = time.time()
    try:
        yield
    finally:
        execution_time_ms = (time.time() - start_time) * 1000

        # Record the operation time
        if operation_type == "api":
            _record_api_call(operation_name, execution_time_ms)
        elif operation_type == "database":
            _record_database_query(operation_name, execution_time_ms)
        elif operation_type == "external_api":
            _record_external_api_call(operation_name, execution_time_ms)

        # Log slow operations
        if execution_time_ms > _slow_threshold_ms:
            logger.warning(
                f"Slow {operation_type} operation: {operation_name} took {execution_time_ms:.2f}ms"
            )


def track_execution_time(
    operation_type: str, operation_name: Optional[str] = None
) -> Callable[[F], F]:
    """
    Decorator to track function execution time.

    Args:
        operation_type: Type of operation (api, database, external_api)
        operation_name: Name of the specific operation (defaults to function name)

    Example:
        @track_execution_time('database')
        async def get_user_by_id(db, user_id):
            ...
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            name = operation_name or func.__name__
            with track_operation_time(operation_type, name):
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            name = operation_name or func.__name__
            with track_operation_time(operation_type, name):
                return func(*args, **kwargs)

        # Use the appropriate wrapper based on whether the function is async
        if asyncio.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        return cast(F, sync_wrapper)

    return decorator


def record_cache_access(cache_type: str, hit: bool) -> None:
    """
    Record a cache hit or miss.

    Args:
        cache_type: Type of cache ('price' or 'conversion')
        hit: Whether the cache access was a hit (True) or miss (False)
    """
    global _performance_metrics

    # Update overall cache metrics
    if hit:
        _performance_metrics["cache"]["hits"] += 1
    else:
        _performance_metrics["cache"]["misses"] += 1

    # Update cache type specific metrics
    if cache_type in _performance_metrics["cache"]["by_type"]:
        if hit:
            _performance_metrics["cache"]["by_type"][cache_type]["hits"] += 1
        else:
            _performance_metrics["cache"]["by_type"][cache_type]["misses"] += 1


def _record_api_call(endpoint: str, execution_time_ms: float) -> None:
    """
    Record an API call with its execution time.

    Args:
        endpoint: API endpoint path
        execution_time_ms: Execution time in milliseconds
    """
    global _performance_metrics

    # Update total API calls
    _performance_metrics["api_calls"]["total"] += 1

    # Update endpoint-specific metrics
    if endpoint not in _performance_metrics["api_calls"]["by_endpoint"]:
        _performance_metrics["api_calls"]["by_endpoint"][endpoint] = {
            "count": 0,
            "total_time_ms": 0,
            "avg_time_ms": 0,
            "min_time_ms": float("inf"),
            "max_time_ms": 0,
        }

    endpoint_metrics = _performance_metrics["api_calls"]["by_endpoint"][endpoint]
    endpoint_metrics["count"] += 1
    endpoint_metrics["total_time_ms"] += execution_time_ms
    endpoint_metrics["avg_time_ms"] = (
        endpoint_metrics["total_time_ms"] / endpoint_metrics["count"]
    )
    endpoint_metrics["min_time_ms"] = min(
        endpoint_metrics["min_time_ms"], execution_time_ms
    )
    endpoint_metrics["max_time_ms"] = max(
        endpoint_metrics["max_time_ms"], execution_time_ms
    )

    # Add to response times history (with limit)
    _performance_metrics["api_calls"]["response_times"].append(execution_time_ms)
    if len(_performance_metrics["api_calls"]["response_times"]) > _max_metrics_history:
        _performance_metrics["api_calls"]["response_times"].pop(0)

    # Record slow operations
    if execution_time_ms > _slow_threshold_ms:
        slow_op = {
            "endpoint": endpoint,
            "execution_time_ms": execution_time_ms,
            "timestamp": datetime.now().isoformat(),
        }
        _performance_metrics["api_calls"]["slow_operations"].append(slow_op)
        if (
            len(_performance_metrics["api_calls"]["slow_operations"])
            > _max_metrics_history
        ):
            _performance_metrics["api_calls"]["slow_operations"].pop(0)


def _record_database_query(query_name: str, execution_time_ms: float) -> None:
    """
    Record a database query with its execution time.

    Args:
        query_name: Name or description of the query
        execution_time_ms: Execution time in milliseconds
    """
    global _performance_metrics

    # Update total queries
    _performance_metrics["database"]["queries"] += 1

    # Add to query times history (with limit)
    _performance_metrics["database"]["query_times"].append(execution_time_ms)
    if len(_performance_metrics["database"]["query_times"]) > _max_metrics_history:
        _performance_metrics["database"]["query_times"].pop(0)

    # Record slow queries
    if execution_time_ms > _slow_threshold_ms:
        slow_query = {
            "query": query_name,
            "execution_time_ms": execution_time_ms,
            "timestamp": datetime.now().isoformat(),
        }
        _performance_metrics["database"]["slow_queries"].append(slow_query)
        if len(_performance_metrics["database"]["slow_queries"]) > _max_metrics_history:
            _performance_metrics["database"]["slow_queries"].pop(0)


def _record_external_api_call(
    service: str, execution_time_ms: float, error: bool = False
) -> None:
    """
    Record an external API call with its execution time.

    Args:
        service: Name of the external service
        execution_time_ms: Execution time in milliseconds
        error: Whether the call resulted in an error
    """
    global _performance_metrics

    # Update total calls
    _performance_metrics["external_apis"]["calls"] += 1

    # Update error count if applicable
    if error:
        _performance_metrics["external_apis"]["errors"] += 1

    # Update service-specific metrics
    if service not in _performance_metrics["external_apis"]["by_service"]:
        _performance_metrics["external_apis"]["by_service"][service] = {
            "calls": 0,
            "errors": 0,
            "total_time_ms": 0,
            "avg_time_ms": 0,
        }

    service_metrics = _performance_metrics["external_apis"]["by_service"][service]
    service_metrics["calls"] += 1
    if error:
        service_metrics["errors"] += 1
    service_metrics["total_time_ms"] += execution_time_ms
    service_metrics["avg_time_ms"] = (
        service_metrics["total_time_ms"] / service_metrics["calls"]
    )


def record_external_api_call(
    service: str, execution_time_ms: float, error: bool = False
) -> None:
    """
    Record an external API call with its execution time.
    Public wrapper for _record_external_api_call.

    Args:
        service: Name of the external service
        execution_time_ms: Execution time in milliseconds
        error: Whether the call resulted in an error
    """
    _record_external_api_call(service, execution_time_ms, error)


def get_performance_metrics() -> Dict[str, Any]:
    """
    Get the current performance metrics.

    Returns:
        Dict containing all performance metrics
    """
    # Create a copy of the metrics to avoid modification during access
    metrics = {**_performance_metrics}

    # Add calculated metrics

    # Cache hit rate
    total_cache_accesses = metrics["cache"]["hits"] + metrics["cache"]["misses"]
    if total_cache_accesses > 0:
        metrics["cache"]["hit_rate"] = metrics["cache"]["hits"] / total_cache_accesses
    else:
        metrics["cache"]["hit_rate"] = 0

    # API response time percentiles
    response_times = metrics["api_calls"]["response_times"]
    if response_times:
        metrics["api_calls"]["percentiles"] = {
            "p50": statistics.median(response_times),
            "p90": (
                statistics.quantiles(response_times, n=10)[8]
                if len(response_times) >= 10
                else None
            ),
            "p95": (
                statistics.quantiles(response_times, n=20)[18]
                if len(response_times) >= 20
                else None
            ),
            "p99": (
                statistics.quantiles(response_times, n=100)[98]
                if len(response_times) >= 100
                else None
            ),
        }

    # Database query time percentiles
    query_times = metrics["database"]["query_times"]
    if query_times:
        metrics["database"]["percentiles"] = {
            "p50": statistics.median(query_times),
            "p90": (
                statistics.quantiles(query_times, n=10)[8]
                if len(query_times) >= 10
                else None
            ),
            "p95": (
                statistics.quantiles(query_times, n=20)[18]
                if len(query_times) >= 20
                else None
            ),
            "p99": (
                statistics.quantiles(query_times, n=100)[98]
                if len(query_times) >= 100
                else None
            ),
        }

    # External API error rate
    if metrics["external_apis"]["calls"] > 0:
        metrics["external_apis"]["error_rate"] = (
            metrics["external_apis"]["errors"] / metrics["external_apis"]["calls"]
        )
    else:
        metrics["external_apis"]["error_rate"] = 0

    return metrics


def reset_performance_metrics() -> None:
    """
    Reset all performance metrics to their initial state.
    """
    global _performance_metrics
    _performance_metrics = {
        "api_calls": {
            "total": 0,
            "by_endpoint": {},
            "response_times": [],
            "slow_operations": [],
        },
        "cache": {
            "hits": 0,
            "misses": 0,
            "by_type": {
                "price": {"hits": 0, "misses": 0},
                "conversion": {"hits": 0, "misses": 0},
            },
        },
        "database": {
            "queries": 0,
            "slow_queries": [],
            "query_times": [],
        },
        "external_apis": {
            "calls": 0,
            "errors": 0,
            "by_service": {},
        },
    }


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track API request performance.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Start timing
        start_time = time.time()

        # Process the request
        response = await call_next(request)

        # Calculate execution time
        execution_time_ms = (time.time() - start_time) * 1000

        # Record the API call
        endpoint = f"{request.method} {request.url.path}"
        _record_api_call(endpoint, execution_time_ms)

        # Add performance headers to response
        response.headers["X-Response-Time-Ms"] = f"{execution_time_ms:.2f}"

        return response


import asyncio
