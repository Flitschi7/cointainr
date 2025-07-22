"""
URL rewriting middleware for handling hardcoded API URLs in the frontend.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from fastapi import FastAPI
import logging

logger = logging.getLogger(__name__)


class URLRewriteMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle requests with hardcoded URLs in the frontend.
    This middleware intercepts 404 responses for API routes and redirects them
    to the correct API endpoint.
    """

    async def dispatch(self, request: Request, call_next):
        # Process the request normally first
        response = await call_next(request)

        # If the response is a 404 and the URL contains a hardcoded port
        if response.status_code == 404 and "127.0.0.1:8000" in str(request.url):
            # Extract the path from the URL
            path = request.url.path

            # If it's an API request, try to handle it
            if path.startswith("/api/"):
                logger.info(f"Rewriting URL from {request.url} to {path}")

                # Create a new request to the correct API endpoint
                # This is a simplified approach - in a real implementation,
                # we would need to properly forward the request
                return JSONResponse(
                    status_code=307,
                    content={"detail": f"API endpoint moved to {path}"},
                    headers={"Location": path},
                )

        return response


def setup_url_rewrite_middleware(app: FastAPI):
    """
    Set up URL rewriting middleware.
    """
    app.add_middleware(URLRewriteMiddleware)
