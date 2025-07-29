"""
Authentication middleware for FastAPI.

This middleware handles session validation for protected routes and provides
proper error responses for unauthorized access attempts.
"""

import logging
from datetime import datetime
from typing import Callable, Set
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.services.auth_service import auth_service
from app.db.session import SessionLocal
from app.core.auth_config import auth_settings

# Set up logger
logger = logging.getLogger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for handling authentication and session validation.

    This middleware:
    1. Checks if authentication is enabled
    2. Validates session tokens for protected routes
    3. Skips authentication for login endpoints and static files
    4. Provides proper error responses for unauthorized access
    """

    def __init__(self, app: ASGIApp):
        """Initialize the authentication middleware."""
        super().__init__(app)

        # Define paths that should skip authentication
        self.skip_auth_paths: Set[str] = {
            # Health check endpoints
            "/api/health",
            "/api/v1/health",
            # Authentication endpoints (must be accessible without auth)
            "/api/v1/auth/login",
            "/api/v1/auth/logout",
            "/api/v1/auth/status",
            "/api/v1/auth/demo-credentials",
            "/api/v1/auth/config",
            # API documentation (if enabled)
            "/docs",
            "/redoc",
            "/openapi.json",
            # Static files and assets
            "/favicon.ico",
            "/favicon.png",
        }

        # Define path prefixes that should skip authentication
        self.skip_auth_prefixes: Set[str] = {
            # Frontend static assets
            "/_app/",
            "/static/",
            # API static files
            "/api/static/",
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and validate authentication if required.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            The response or an authentication error response
        """
        # Check if authentication is enabled
        if not auth_settings.auth_enabled:
            # Authentication is disabled, proceed normally
            return await call_next(request)

        # Check if this path should skip authentication
        if self._should_skip_auth(request.url.path):
            return await call_next(request)

        # Extract session token from cookies or headers
        session_token = self._extract_session_token(request)
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "Unknown")

        if not session_token:
            # Log security event for missing session token
            logger.warning(
                f"Authentication required: No session token for protected route",
                extra={
                    "event_type": "auth_missing_token",
                    "path": request.url.path,
                    "method": request.method,
                    "client_ip": client_ip,
                    "user_agent": user_agent,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            return self._create_unauthorized_response("Authentication required")

        # Validate session token
        try:
            async with SessionLocal() as db:
                is_valid = await auth_service.validate_session(db, session_token)

                if not is_valid:
                    # Log security event for invalid session
                    logger.warning(
                        f"Authentication failed: Invalid or expired session token",
                        extra={
                            "event_type": "auth_invalid_session",
                            "path": request.url.path,
                            "method": request.method,
                            "client_ip": client_ip,
                            "user_agent": user_agent,
                            "session_token_prefix": (
                                session_token[:8] + "..."
                                if len(session_token) > 8
                                else session_token
                            ),
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    )
                    return self._create_unauthorized_response(
                        "Invalid or expired session"
                    )

                # Add session info to request state for use in route handlers
                session_info = await auth_service.get_session_info(db, session_token)
                if session_info:
                    request.state.session_token = session_token
                    request.state.username = session_info.username
                    request.state.authenticated = True

                    # Log successful authentication for security monitoring
                    logger.debug(
                        f"Authentication successful for user: {session_info.username}",
                        extra={
                            "event_type": "auth_success",
                            "username": session_info.username,
                            "path": request.url.path,
                            "method": request.method,
                            "client_ip": client_ip,
                            "session_expires_at": session_info.expires_at.isoformat(),
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    )
                else:
                    # Log security event for session validation failure
                    logger.error(
                        f"Session validation failed: Unable to retrieve session info",
                        extra={
                            "event_type": "auth_session_validation_failed",
                            "path": request.url.path,
                            "method": request.method,
                            "client_ip": client_ip,
                            "session_token_prefix": (
                                session_token[:8] + "..."
                                if len(session_token) > 8
                                else session_token
                            ),
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    )
                    return self._create_unauthorized_response(
                        "Session validation failed"
                    )

        except Exception as e:
            # Log security event for authentication error
            logger.error(
                f"Authentication error: {str(e)}",
                extra={
                    "event_type": "auth_error",
                    "path": request.url.path,
                    "method": request.method,
                    "client_ip": client_ip,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            return self._create_unauthorized_response("Authentication error")

        # Session is valid, proceed with the request
        return await call_next(request)

    def _should_skip_auth(self, path: str) -> bool:
        """
        Determine if authentication should be skipped for the given path.

        Args:
            path: The request path

        Returns:
            bool: True if authentication should be skipped
        """
        # Check exact path matches
        if path in self.skip_auth_paths:
            return True

        # Check path prefixes
        for prefix in self.skip_auth_prefixes:
            if path.startswith(prefix):
                return True

        # Check for static file extensions
        static_extensions = {
            ".js",
            ".css",
            ".png",
            ".svg",
            ".ico",
            ".jpg",
            ".jpeg",
            ".gif",
            ".woff",
            ".woff2",
            ".ttf",
        }
        if any(path.lower().endswith(ext) for ext in static_extensions):
            return True

        return False

    def _extract_session_token(self, request: Request) -> str | None:
        """
        Extract session token from request cookies or headers.

        Args:
            request: The incoming request

        Returns:
            str | None: The session token if found, None otherwise
        """
        # First, try to get from cookies (preferred method)
        session_token = request.cookies.get("session_token")
        if session_token:
            return session_token

        # Fallback to Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]  # Remove "Bearer " prefix

        # Fallback to custom header
        return request.headers.get("X-Session-Token")

    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP address from request headers.

        Args:
            request: The incoming request

        Returns:
            str: The client IP address
        """
        # Check for forwarded headers (common in reverse proxy setups)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # X-Forwarded-For can contain multiple IPs, take the first one
            return forwarded_for.split(",")[0].strip()

        # Check for real IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fallback to client host
        if hasattr(request, "client") and request.client:
            return request.client.host

        return "unknown"

    def _create_unauthorized_response(self, message: str) -> JSONResponse:
        """
        Create a standardized unauthorized response.

        Args:
            message: The error message to include

        Returns:
            JSONResponse: The unauthorized response
        """
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "success": False,
                "error": "Unauthorized",
                "message": message,
                "error_code": "AUTH_REQUIRED",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
