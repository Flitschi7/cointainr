from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import logging

from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    AuthStatusResponse,
    AuthErrorResponse,
)
from app.services.auth_service import auth_service
from app.db.session import SessionLocal
from app.core.auth_config import auth_settings

logger = logging.getLogger(__name__)

router = APIRouter()


def get_db_dependency():
    """
    Dependency provider for async DB session.
    Yields an AsyncSession instance.
    """

    async def _get_db():
        async with SessionLocal() as session:
            yield session

    return Depends(_get_db)


db_dep = get_db_dependency()


def get_session_token_from_request(request: Request) -> Optional[str]:
    """
    Extract session token from request cookies or headers.

    Args:
        request: FastAPI request object

    Returns:
        Optional[str]: Session token if found, None otherwise
    """
    # Try to get from cookie first (preferred method)
    session_token = request.cookies.get("session_token")

    # Fallback to Authorization header
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header[7:]  # Remove "Bearer " prefix

    return session_token


@router.post("/login", response_model=LoginResponse)
async def login(
    *,
    db: AsyncSession = db_dep,
    login_request: LoginRequest,
    response: Response,
) -> LoginResponse:
    """
    Authenticate user with username and password.
    Creates a session and sets secure session cookie on success.

    Args:
        db: Database session
        login_request: Login credentials
        response: FastAPI response object for setting cookies

    Returns:
        LoginResponse: Authentication result with session information
    """
    try:
        # Check if authentication is enabled
        if not auth_service.is_auth_enabled():
            logger.warning("Login attempt when authentication is disabled")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication is not enabled",
            )

        # Perform login
        login_result = await auth_service.login(db, login_request)

        if login_result.success and login_result.session_token:
            # Set secure session cookie
            response.set_cookie(
                key="session_token",
                value=login_result.session_token,
                httponly=True,  # Prevent XSS attacks
                secure=auth_settings.ENVIRONMENT
                == "production",  # HTTPS only in production
                samesite="lax",  # CSRF protection
                max_age=auth_settings.SESSION_TIMEOUT_HOURS
                * 3600,  # Convert hours to seconds
            )

            logger.info(f"Successful login for user: {login_request.username}")

            # Keep session token in response for frontend compatibility
            # Note: This is less secure than HTTP-only cookies, but needed for current frontend implementation

        else:
            logger.warning(f"Failed login attempt for user: {login_request.username}")

        return login_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login",
        )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    *,
    db: AsyncSession = db_dep,
    request: Request,
    response: Response,
) -> LogoutResponse:
    """
    Logout user by invalidating their session.
    Clears the session cookie.

    Args:
        db: Database session
        request: FastAPI request object
        response: FastAPI response object for clearing cookies

    Returns:
        LogoutResponse: Logout result
    """
    try:
        # Get session token from request
        session_token = get_session_token_from_request(request)

        if not session_token:
            logger.debug("Logout attempt without session token")
            # Clear cookie anyway in case it exists but is invalid
            response.delete_cookie(key="session_token")
            return LogoutResponse(success=True, message="No active session found")

        # Perform logout
        logout_result = await auth_service.logout(db, session_token)

        # Clear session cookie regardless of logout result
        response.delete_cookie(key="session_token")

        if logout_result.success:
            logger.info("Successful logout")
        else:
            logger.debug("Logout attempt with invalid session")

        return logout_result

    except Exception as e:
        logger.error(f"Unexpected error during logout: {str(e)}")
        # Still clear the cookie on error
        response.delete_cookie(key="session_token")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during logout",
        )


@router.get("/status", response_model=AuthStatusResponse)
async def auth_status(
    *,
    db: AsyncSession = db_dep,
    request: Request,
) -> AuthStatusResponse:
    """
    Get current authentication status for the session.

    Args:
        db: Database session
        request: FastAPI request object

    Returns:
        AuthStatusResponse: Current authentication status
    """
    try:
        # Check if authentication is enabled
        if not auth_service.is_auth_enabled():
            return AuthStatusResponse(
                authenticated=False,
                demo_mode=False,
                session_valid=False,
            )

        # Get session token from request
        session_token = get_session_token_from_request(request)

        if not session_token:
            return AuthStatusResponse(
                authenticated=False,
                demo_mode=auth_settings.DEMO_MODE,
                session_valid=False,
            )

        # Get authentication status
        auth_status_result = await auth_service.get_auth_status(db, session_token)

        return auth_status_result

    except Exception as e:
        logger.error(f"Unexpected error getting auth status: {str(e)}")
        return AuthStatusResponse(
            authenticated=False,
            demo_mode=auth_settings.DEMO_MODE,
            session_valid=False,
        )


@router.get("/demo-credentials")
async def get_demo_credentials():
    """
    Get demo mode credentials if demo mode is enabled.
    This endpoint is only available when demo mode is active.

    Returns:
        Dict: Demo credentials or error message
    """
    try:
        if not auth_service.is_auth_enabled():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication is not enabled",
            )

        demo_credentials = auth_service.get_demo_credentials()

        if demo_credentials:
            return {
                "demo_mode": True,
                "credentials": demo_credentials,
                "message": "Demo mode is active. Use these credentials to login.",
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Demo mode is not enabled"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting demo credentials: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred retrieving demo credentials",
        )


@router.get("/config")
async def get_auth_config():
    """
    Get authentication configuration information.
    Returns public configuration details without sensitive information.

    Returns:
        Dict: Authentication configuration
    """
    try:
        return {
            "auth_enabled": auth_service.is_auth_enabled(),
            "demo_mode": auth_settings.DEMO_MODE,
            "session_timeout_hours": auth_settings.SESSION_TIMEOUT_HOURS,
            "environment": auth_settings.ENVIRONMENT,
        }

    except Exception as e:
        logger.error(f"Unexpected error getting auth config: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred retrieving authentication configuration",
        )
