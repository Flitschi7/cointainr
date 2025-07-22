"""
API logging middleware for debugging API requests.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import logging

logger = logging.getLogger(__name__)


class APILoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log API requests and responses for debugging.
    """

    async def dispatch(self, request: Request, call_next):
        # Log the request
        path = request.url.path
        if path.startswith("/api/"):
            logger.info(f"API Request: {request.method} {path}")
            logger.info(f"  Headers: {dict(request.headers)}")

            # Process the request
            response = await call_next(request)

            # Log the response
            logger.info(
                f"API Response: {response.status_code} for {request.method} {path}"
            )
            return response
        else:
            # Non-API request, just process normally
            return await call_next(request)


def setup_api_logging_middleware(app):
    """
    Set up API logging middleware.
    """
    app.add_middleware(APILoggingMiddleware)
