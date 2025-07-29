from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional


# --- Authentication Request Schemas ---


class LoginRequest(BaseModel):
    """
    Schema for login request payload.
    Contains username and password for authentication.
    """

    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=200)


class LogoutRequest(BaseModel):
    """
    Schema for logout request payload.
    Contains session token to invalidate.
    """

    session_token: str = Field(..., min_length=1)


# --- Authentication Response Schemas ---


class LoginResponse(BaseModel):
    """
    Schema for login response.
    Contains authentication result and session information.
    """

    success: bool
    session_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    demo_mode: bool = False
    username: Optional[str] = None
    message: Optional[str] = None


class LogoutResponse(BaseModel):
    """
    Schema for logout response.
    Confirms successful logout operation.
    """

    success: bool
    message: str = "Successfully logged out"


class AuthStatusResponse(BaseModel):
    """
    Schema for authentication status response.
    Contains current authentication state information.
    """

    authenticated: bool
    username: Optional[str] = None
    demo_mode: bool = False
    expires_at: Optional[datetime] = None
    session_valid: bool = False


# --- Session Management Schemas ---


class SessionCreate(BaseModel):
    """
    Schema for creating a new session.
    Used internally by the authentication service.
    """

    username: str
    expires_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionRead(BaseModel):
    """
    Schema for reading session information.
    Contains session details without sensitive data.
    """

    id: str
    username: str
    created_at: datetime
    expires_at: datetime
    is_active: bool
    last_activity: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SessionUpdate(BaseModel):
    """
    Schema for updating session information.
    Allows updating session activity and status.
    """

    is_active: Optional[bool] = None
    last_activity: Optional[datetime] = None


# --- Error Response Schemas ---


class AuthErrorResponse(BaseModel):
    """
    Schema for authentication error responses.
    Provides structured error information.
    """

    success: bool = False
    error: str
    message: str
    error_code: Optional[str] = None
