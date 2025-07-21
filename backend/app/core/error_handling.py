"""
Centralized error handling module for the Cointainr backend.

This module provides standardized error handling functions and classes
to ensure consistent error responses across the API.
"""

import logging
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, Type, List, Union
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

# Set up logger
logger = logging.getLogger(__name__)


class ErrorCategory:
    """Error categories for better error classification and handling."""

    VALIDATION = "validation_error"
    DATABASE = "database_error"
    EXTERNAL_API = "external_api_error"
    AUTHENTICATION = "authentication_error"
    AUTHORIZATION = "authorization_error"
    RATE_LIMIT = "rate_limit_error"
    NOT_FOUND = "not_found_error"
    CACHE = "cache_error"
    INTERNAL = "internal_error"
    UNKNOWN = "unknown_error"


class StandardError(Exception):
    """
    Standard error class for consistent error handling.

    This class extends the base Exception class with additional fields
    for better error reporting and handling.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        category: str = ErrorCategory.UNKNOWN,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        """
        Initialize a StandardError instance.

        Args:
            message: Human-readable error message
            status_code: HTTP status code
            category: Error category for classification
            details: Additional error details
            original_error: Original exception that caused this error
        """
        self.message = message
        self.status_code = status_code
        self.category = category
        self.details = details or {}
        self.original_error = original_error
        self.timestamp = datetime.utcnow().isoformat()

        # Add original error details if available
        if original_error:
            self.details["original_error"] = str(original_error)

            # Add traceback for internal errors in development
            if category == ErrorCategory.INTERNAL:
                self.details["traceback"] = traceback.format_exc()

        super().__init__(self.message)


class ValidationError(StandardError):
    """Error raised when input validation fails."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        """Initialize a ValidationError instance."""
        super().__init__(
            message=message,
            status_code=422,
            category=ErrorCategory.VALIDATION,
            details=details,
            original_error=original_error,
        )


class DatabaseError(StandardError):
    """Error raised when a database operation fails."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        """Initialize a DatabaseError instance."""
        super().__init__(
            message=message,
            status_code=500,
            category=ErrorCategory.DATABASE,
            details=details,
            original_error=original_error,
        )


class ExternalAPIError(StandardError):
    """Error raised when an external API call fails."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
        status_code: int = 502,
    ):
        """Initialize an ExternalAPIError instance."""
        super().__init__(
            message=message,
            status_code=status_code,
            category=ErrorCategory.EXTERNAL_API,
            details=details,
            original_error=original_error,
        )


class NotFoundError(StandardError):
    """Error raised when a requested resource is not found."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        """Initialize a NotFoundError instance."""
        super().__init__(
            message=message,
            status_code=404,
            category=ErrorCategory.NOT_FOUND,
            details=details,
            original_error=original_error,
        )


class CacheError(StandardError):
    """Error raised when a cache operation fails."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        """Initialize a CacheError instance."""
        super().__init__(
            message=message,
            status_code=500,
            category=ErrorCategory.CACHE,
            details=details,
            original_error=original_error,
        )


def format_error_response(
    error: Union[StandardError, Exception],
    include_details: bool = True,
    include_traceback: bool = False,
) -> Dict[str, Any]:
    """
    Format an error into a standardized response dictionary.

    Args:
        error: Error instance to format
        include_details: Whether to include error details
        include_traceback: Whether to include traceback

    Returns:
        Standardized error response dictionary
    """
    if isinstance(error, StandardError):
        response = {
            "error": True,
            "message": error.message,
            "category": error.category,
            "status_code": error.status_code,
            "timestamp": error.timestamp,
        }

        if include_details and error.details:
            # Filter out traceback if not requested
            details = error.details.copy()
            if not include_traceback and "traceback" in details:
                del details["traceback"]
            response["details"] = details
    else:
        # Handle standard exceptions
        response = {
            "error": True,
            "message": str(error),
            "category": ErrorCategory.UNKNOWN,
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if include_traceback:
            response["details"] = {"traceback": traceback.format_exc()}

    return response


def log_error(
    error: Union[StandardError, Exception],
    request: Optional[Request] = None,
    log_level: int = logging.ERROR,
) -> None:
    """
    Log an error with standardized format.

    Args:
        error: Error to log
        request: Request that caused the error
        log_level: Logging level
    """
    # Prepare log message
    if isinstance(error, StandardError):
        log_message = f"{error.category}: {error.message}"
        if error.original_error:
            log_message += f" (Original: {error.original_error})"
    else:
        log_message = f"Unhandled exception: {str(error)}"

    # Add request information if available
    if request:
        log_message += f" - Method: {request.method}, URL: {request.url.path}"

    # Log with appropriate level
    logger.log(log_level, log_message)

    # Log traceback for internal errors
    if log_level >= logging.ERROR:
        logger.debug(traceback.format_exc())


async def handle_standard_error(request: Request, exc: StandardError) -> JSONResponse:
    """
    Handle StandardError exceptions.

    Args:
        request: Request that caused the error
        exc: StandardError instance

    Returns:
        JSONResponse with standardized error format
    """
    # Get request ID from request state or generate a new one
    request_id = getattr(request.state, "request_id", None)

    # Add request ID to error details
    if request_id and hasattr(exc, "details") and exc.details is not None:
        exc.details["request_id"] = request_id

    # Log the error with request ID
    log_error(exc, request)

    # Format error response
    error_response = format_error_response(exc)

    # Add request ID to response
    if request_id and "request_id" not in error_response:
        error_response["request_id"] = request_id

    # Return standardized response
    response = JSONResponse(
        status_code=exc.status_code,
        content=error_response,
    )

    # Add request ID to response headers
    if request_id:
        response.headers["X-Request-ID"] = request_id

    return response


async def handle_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handle FastAPI RequestValidationError exceptions.

    Args:
        request: Request that caused the error
        exc: RequestValidationError instance

    Returns:
        JSONResponse with standardized error format
    """
    # Get request ID from request state or generate a new one
    request_id = getattr(request.state, "request_id", None)

    # Convert validation errors to a readable format
    error_details = {"validation_errors": []}

    for error in exc.errors():
        error_details["validation_errors"].append(
            {
                "loc": error.get("loc", []),
                "msg": error.get("msg", ""),
                "type": error.get("type", ""),
            }
        )

    # Add request ID to error details
    if request_id:
        error_details["request_id"] = request_id

    # Create StandardError
    std_error = ValidationError(
        message="Request validation failed",
        details=error_details,
        original_error=exc,
    )

    # Log the error with request ID
    log_error(std_error, request)

    # Format error response
    error_response = format_error_response(std_error)

    # Add request ID to response
    if request_id and "request_id" not in error_response:
        error_response["request_id"] = request_id

    # Return standardized response
    response = JSONResponse(
        status_code=std_error.status_code,
        content=error_response,
    )

    # Add request ID to response headers
    if request_id:
        response.headers["X-Request-ID"] = request_id

    return response


async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle FastAPI HTTPException exceptions.

    Args:
        request: Request that caused the error
        exc: HTTPException instance

    Returns:
        JSONResponse with standardized error format
    """
    # Get request ID from request state or generate a new one
    request_id = getattr(request.state, "request_id", None)

    # Map HTTP status code to error category
    category = ErrorCategory.UNKNOWN
    if exc.status_code == 404:
        category = ErrorCategory.NOT_FOUND
    elif exc.status_code == 401:
        category = ErrorCategory.AUTHENTICATION
    elif exc.status_code == 403:
        category = ErrorCategory.AUTHORIZATION
    elif exc.status_code == 429:
        category = ErrorCategory.RATE_LIMIT
    elif 400 <= exc.status_code < 500:
        category = ErrorCategory.VALIDATION
    elif exc.status_code >= 500:
        category = ErrorCategory.INTERNAL

    # Create error details with request ID
    details = {"error_type": "HTTPException"}
    if request_id:
        details["request_id"] = request_id

    # Create StandardError
    std_error = StandardError(
        message=str(exc.detail),
        status_code=exc.status_code,
        category=category,
        details=details,
        original_error=exc,
    )

    # Log the error with request ID
    log_error(std_error, request)

    # Format error response
    error_response = format_error_response(std_error)

    # Add request ID to response
    if request_id and "request_id" not in error_response:
        error_response["request_id"] = request_id

    # Return standardized response
    response = JSONResponse(
        status_code=std_error.status_code,
        content=error_response,
    )

    # Add request ID to response headers
    if request_id:
        response.headers["X-Request-ID"] = request_id

    return response


async def handle_sqlalchemy_error(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    """
    Handle SQLAlchemy errors.

    Args:
        request: Request that caused the error
        exc: SQLAlchemyError instance

    Returns:
        JSONResponse with standardized error format
    """
    # Get request ID from request state or generate a new one
    request_id = getattr(request.state, "request_id", None)

    # Create error details with request ID
    details = {"error_type": type(exc).__name__}
    if request_id:
        details["request_id"] = request_id

    # Create DatabaseError
    std_error = DatabaseError(
        message="Database operation failed",
        details=details,
        original_error=exc,
    )

    # Log the error with request ID
    log_error(std_error, request)

    # Format error response
    error_response = format_error_response(std_error)

    # Add request ID to response
    if request_id and "request_id" not in error_response:
        error_response["request_id"] = request_id

    # Return standardized response
    response = JSONResponse(
        status_code=std_error.status_code,
        content=error_response,
    )

    # Add request ID to response headers
    if request_id:
        response.headers["X-Request-ID"] = request_id

    return response


async def handle_unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle any unhandled exceptions.

    Args:
        request: Request that caused the error
        exc: Exception instance

    Returns:
        JSONResponse with standardized error format
    """
    # Get request ID from request state or generate a new one
    request_id = getattr(request.state, "request_id", None)

    # Create error details with request ID
    details = {"error_type": type(exc).__name__}
    if request_id:
        details["request_id"] = request_id

    # Create StandardError
    std_error = StandardError(
        message="Internal server error",
        status_code=500,
        category=ErrorCategory.INTERNAL,
        details=details,
        original_error=exc,
    )

    # Log the error with request ID
    log_error(std_error, request)

    # Format error response
    error_response = format_error_response(std_error)

    # Add request ID to response
    if request_id and "request_id" not in error_response:
        error_response["request_id"] = request_id

    # Return standardized response
    response = JSONResponse(
        status_code=std_error.status_code,
        content=error_response,
    )

    # Add request ID to response headers
    if request_id:
        response.headers["X-Request-ID"] = request_id

    return response


def setup_exception_handlers(app):
    """
    Set up exception handlers for the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    # Register handlers for specific exception types
    app.add_exception_handler(StandardError, handle_standard_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(HTTPException, handle_http_exception)
    app.add_exception_handler(SQLAlchemyError, handle_sqlalchemy_error)
    app.add_exception_handler(Exception, handle_unhandled_exception)


def handle_external_api_error(
    error: Exception,
    service_name: str,
    operation: str,
    allow_cache_fallback: bool = True,
    cache_fallback_data: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Handle errors from external API calls with graceful degradation.

    This function provides standardized error handling for external API calls,
    with support for cache fallback when available.

    Args:
        error: Original exception from the API call
        service_name: Name of the external service (e.g., "Finnhub", "CoinGecko")
        operation: Operation being performed (e.g., "get_stock_price")
        allow_cache_fallback: Whether to allow fallback to cached data
        cache_fallback_data: Cached data to use as fallback

    Returns:
        Error response dictionary with fallback data if available

    Raises:
        ExternalAPIError: If no fallback is available or allowed
    """
    # Log the error
    logger.error(
        f"External API error in {service_name}.{operation}: {str(error)}",
        exc_info=True,
    )

    # Prepare error details
    error_details = {
        "service": service_name,
        "operation": operation,
        "error_type": type(error).__name__,
        "cache_fallback_available": allow_cache_fallback
        and cache_fallback_data is not None,
    }

    # Check if we can use cache fallback
    if allow_cache_fallback and cache_fallback_data is not None:
        # Return response with fallback data and warning
        return {
            "data": cache_fallback_data,
            "warning": f"{service_name} API error, using cached data",
            "error_details": error_details,
            "using_cache_fallback": True,
            "timestamp": datetime.utcnow().isoformat(),
        }

    # No fallback available, raise standardized error
    raise ExternalAPIError(
        message=f"{service_name} API error: {str(error)}",
        details=error_details,
        original_error=error,
    )
