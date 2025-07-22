"""
API proxy middleware for handling hardcoded URLs.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, RedirectResponse
from fastapi import FastAPI
import logging

logger = logging.getLogger(__name__)


class APIProxyMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle requests with hardcoded URLs.
    This middleware intercepts requests with hardcoded URLs and redirects them
    to the correct endpoints.
    """

    async def dispatch(self, request: Request, call_next):
        # Get the request URL
        url = str(request.url)

        # Check if the URL contains a hardcoded port
        if "127.0.0.1:8000" in url:
            # Extract the path and create a new URL with the correct port
            path = request.url.path
            new_url = url.replace("127.0.0.1:8000", request.base_url.netloc)
            logger.info(f"Redirecting from {url} to {new_url}")
            return RedirectResponse(url=new_url)

        # Process the request normally
        return await call_next(request)


def setup_api_proxy_middleware(app: FastAPI):
    """
    Set up API proxy middleware.
    """
    app.add_middleware(APIProxyMiddleware)
