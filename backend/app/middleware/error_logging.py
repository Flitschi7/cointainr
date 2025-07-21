"""
Error logging middleware for FastAPI.

This middleware adds request IDs to all requests and enhances error logging.
"""

import logging
import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Set up logger
logger = logging.getLogger(__name__)


class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for enhanced error logging and request tracking.

    This middleware:
    1. Adds a unique request ID to each request
    2. Logs request details
    3. Logs response details including timing
    4. Provides detailed error logging
    """

    def __init__(self, app: ASGIApp):
        """Initialize the middleware."""
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and add error logging.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            The response
        """
        # Generate unique request ID
        request_id = str(uuid.uuid4())

        # Add request ID to request state
        request.state.request_id = request_id

        # Start timer
        start_time = time.time()

        # Log request details
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_host": request.client.host if request.client else None,
            },
        )

        try:
            # Process the request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            # Log response details
            logger.info(
                f"Request completed: {request.method} {request.url.path} - {response.status_code}",
                extra={
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )

            return response
        except Exception as exc:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log error details
            logger.error(
                f"Request failed: {request.method} {request.url.path} - {str(exc)}",
                extra={
                    "request_id": request_id,
                    "duration_ms": duration_ms,
                    "error_type": type(exc).__name__,
                },
                exc_info=True,
            )

            # Re-raise the exception for the exception handlers
            raise
