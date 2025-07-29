import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from sqlalchemy.exc import SQLAlchemyError

from app.models.session import Session
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    AuthStatusResponse,
    SessionCreate,
    SessionRead,
)
from app.core.auth_config import auth_settings

logger = logging.getLogger(__name__)


class AuthService:
    """
    Core authentication service that handles credential validation,
    session creation, and session management for the Cointainr application.
    """

    def __init__(self):
        self.settings = auth_settings

    async def validate_credentials(self, username: str, password: str) -> bool:
        """
        Validate user credentials against configured authentication settings.

        Args:
            username: The username to validate
            password: The password to validate

        Returns:
            bool: True if credentials are valid, False otherwise
        """
        try:
            # Check if authentication is enabled
            if not self.settings.auth_enabled:
                logger.warning(
                    "Authentication validation attempted but auth is disabled"
                )
                return False

            # Validate against configured credentials
            is_valid = (
                username == self.settings.AUTH_USER
                and password == self.settings.AUTH_PASSWORD
            )

            if is_valid:
                logger.info(f"Successful authentication for user: {username}")
            else:
                logger.warning(f"Failed authentication attempt for user: {username}")

            return is_valid

        except Exception as e:
            logger.error(f"Error during credential validation: {str(e)}")
            return False

    async def create_session(self, db: AsyncSession, username: str) -> Optional[str]:
        """
        Create a new authentication session for a user.

        Args:
            db: Database session
            username: Username for the session

        Returns:
            Optional[str]: Session token if successful, None if failed
        """
        try:
            # Generate secure session token
            session_token = self._generate_session_token()

            # Calculate expiry time
            expires_at = datetime.utcnow() + timedelta(
                hours=self.settings.SESSION_TIMEOUT_HOURS
            )

            # Create session record
            session = Session(
                id=session_token,
                username=username,
                expires_at=expires_at,
                is_active=True,
            )

            db.add(session)
            await db.commit()
            await db.refresh(session)

            logger.info(
                f"Created session for user: {username}, expires at: {expires_at}"
            )
            return session_token

        except SQLAlchemyError as e:
            logger.error(f"Database error creating session: {str(e)}")
            await db.rollback()
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating session: {str(e)}")
            await db.rollback()
            return None

    async def validate_session(self, db: AsyncSession, session_token: str) -> bool:
        """
        Validate if a session token is valid and active.

        Args:
            db: Database session
            session_token: The session token to validate

        Returns:
            bool: True if session is valid, False otherwise
        """
        try:
            # Query for the session
            result = await db.execute(
                select(Session).where(Session.id == session_token)
            )
            session = result.scalar_one_or_none()

            if not session:
                logger.debug(f"Session not found: {session_token}")
                return False

            # Check if session is valid (active and not expired)
            if not session.is_active or datetime.utcnow() > session.expires_at:
                logger.debug(f"Session invalid: {session_token}")
                return False

            # Update last activity
            session.last_activity = datetime.utcnow()
            await db.commit()
            await db.refresh(session)

            logger.debug(f"Session validated for user: {session.username}")
            return True

        except SQLAlchemyError as e:
            logger.error(f"Database error validating session: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error validating session: {str(e)}")
            return False

    async def get_session_info(
        self, db: AsyncSession, session_token: str
    ) -> Optional[SessionRead]:
        """
        Get session information for a valid session token.

        Args:
            db: Database session
            session_token: The session token to get info for

        Returns:
            Optional[SessionRead]: Session information if valid, None otherwise
        """
        try:
            result = await db.execute(
                select(Session).where(Session.id == session_token)
            )
            session = result.scalar_one_or_none()

            if (
                not session
                or not session.is_active
                or datetime.utcnow() > session.expires_at
            ):
                return None

            return SessionRead.model_validate(session)

        except SQLAlchemyError as e:
            logger.error(f"Database error getting session info: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting session info: {str(e)}")
            return None

    async def invalidate_session(self, db: AsyncSession, session_token: str) -> bool:
        """
        Invalidate a specific session token.

        Args:
            db: Database session
            session_token: The session token to invalidate

        Returns:
            bool: True if session was invalidated, False otherwise
        """
        try:
            result = await db.execute(
                select(Session).where(Session.id == session_token)
            )
            session = result.scalar_one_or_none()

            if not session:
                logger.debug(f"Session not found for invalidation: {session_token}")
                return False

            session.is_active = False
            await db.commit()
            await db.refresh(session)

            logger.info(f"Session invalidated for user: {session.username}")
            return True

        except SQLAlchemyError as e:
            logger.error(f"Database error invalidating session: {str(e)}")
            await db.rollback()
            return False
        except Exception as e:
            logger.error(f"Unexpected error invalidating session: {str(e)}")
            await db.rollback()
            return False

    async def cleanup_expired_sessions(self, db: AsyncSession) -> int:
        """
        Clean up expired sessions from the database.

        Args:
            db: Database session

        Returns:
            int: Number of sessions cleaned up
        """
        try:
            # Get expired sessions for logging before deletion
            expired_sessions_result = await db.execute(
                select(Session).where(Session.expires_at < datetime.utcnow())
            )
            expired_sessions = expired_sessions_result.scalars().all()

            # Log expired sessions for security monitoring
            for session in expired_sessions:
                logger.info(
                    f"Cleaning up expired session",
                    extra={
                        "event_type": "session_expired_cleanup",
                        "username": session.username,
                        "session_id": (
                            session.id[:8] + "..."
                            if len(session.id) > 8
                            else session.id
                        ),
                        "created_at": session.created_at.isoformat(),
                        "expires_at": session.expires_at.isoformat(),
                        "was_active": session.is_active,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )

            # Delete expired sessions
            result = await db.execute(
                delete(Session).where(Session.expires_at < datetime.utcnow())
            )

            await db.commit()
            cleaned_count = result.rowcount

            if cleaned_count > 0:
                logger.info(
                    f"Session cleanup completed: {cleaned_count} expired sessions removed",
                    extra={
                        "event_type": "session_cleanup_completed",
                        "sessions_cleaned": cleaned_count,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )

            return cleaned_count

        except SQLAlchemyError as e:
            logger.error(f"Database error cleaning up sessions: {str(e)}")
            await db.rollback()
            return 0
        except Exception as e:
            logger.error(f"Unexpected error cleaning up sessions: {str(e)}")
            await db.rollback()
            return 0

    async def cleanup_user_sessions(self, db: AsyncSession, username: str) -> int:
        """
        Clean up all sessions for a specific user.

        Args:
            db: Database session
            username: Username to clean up sessions for

        Returns:
            int: Number of sessions cleaned up
        """
        try:
            result = await db.execute(
                delete(Session).where(Session.username == username)
            )

            await db.commit()
            cleaned_count = result.rowcount

            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} sessions for user: {username}")

            return cleaned_count

        except SQLAlchemyError as e:
            logger.error(f"Database error cleaning up user sessions: {str(e)}")
            await db.rollback()
            return 0
        except Exception as e:
            logger.error(f"Unexpected error cleaning up user sessions: {str(e)}")
            await db.rollback()
            return 0

    async def login(
        self, db: AsyncSession, login_request: LoginRequest
    ) -> LoginResponse:
        """
        Handle user login with credential validation and session creation.

        Args:
            db: Database session
            login_request: Login request with username and password

        Returns:
            LoginResponse: Login result with session information
        """
        try:
            # Validate credentials
            if not await self.validate_credentials(
                login_request.username, login_request.password
            ):
                return LoginResponse(
                    success=False,
                    message="Invalid username or password",
                )

            # Create session
            session_token = await self.create_session(db, login_request.username)

            if not session_token:
                return LoginResponse(
                    success=False,
                    message="Failed to create session",
                )

            # Calculate expiry time
            expires_at = datetime.utcnow() + timedelta(
                hours=self.settings.SESSION_TIMEOUT_HOURS
            )

            return LoginResponse(
                success=True,
                session_token=session_token,
                expires_at=expires_at,
                demo_mode=self.settings.DEMO_MODE,
                username=login_request.username,
                message="Login successful",
            )

        except Exception as e:
            logger.error(f"Unexpected error during login: {str(e)}")
            return LoginResponse(
                success=False,
                message="An error occurred during login",
            )

    async def logout(self, db: AsyncSession, session_token: str) -> LogoutResponse:
        """
        Handle user logout by invalidating the session.

        Args:
            db: Database session
            session_token: Session token to invalidate

        Returns:
            LogoutResponse: Logout result
        """
        try:
            success = await self.invalidate_session(db, session_token)

            if success:
                return LogoutResponse(
                    success=True,
                    message="Successfully logged out",
                )
            else:
                return LogoutResponse(
                    success=False,
                    message="Session not found or already invalid",
                )

        except Exception as e:
            logger.error(f"Unexpected error during logout: {str(e)}")
            return LogoutResponse(
                success=False,
                message="An error occurred during logout",
            )

    async def get_auth_status(
        self, db: AsyncSession, session_token: str
    ) -> AuthStatusResponse:
        """
        Get authentication status for a session token.

        Args:
            db: Database session
            session_token: Session token to check

        Returns:
            AuthStatusResponse: Authentication status information
        """
        try:
            session_info = await self.get_session_info(db, session_token)

            if session_info:
                return AuthStatusResponse(
                    authenticated=True,
                    username=session_info.username,
                    demo_mode=self.settings.DEMO_MODE,
                    expires_at=session_info.expires_at,
                    session_valid=True,
                )
            else:
                return AuthStatusResponse(
                    authenticated=False,
                    demo_mode=self.settings.DEMO_MODE,
                    session_valid=False,
                )

        except Exception as e:
            logger.error(f"Unexpected error getting auth status: {str(e)}")
            return AuthStatusResponse(
                authenticated=False,
                demo_mode=self.settings.DEMO_MODE,
                session_valid=False,
            )

    def _generate_session_token(self) -> str:
        """
        Generate a cryptographically secure session token.

        Returns:
            str: Secure random session token
        """
        return secrets.token_urlsafe(32)

    def is_auth_enabled(self) -> bool:
        """
        Check if authentication is enabled.

        Returns:
            bool: True if authentication is enabled
        """
        return self.settings.auth_enabled

    async def cleanup_inactive_sessions(
        self, db: AsyncSession, inactive_hours: int = 24
    ) -> int:
        """
        Clean up sessions that have been inactive for a specified period.

        Args:
            db: Database session
            inactive_hours: Hours of inactivity after which to clean up sessions

        Returns:
            int: Number of sessions cleaned up
        """
        try:
            inactive_threshold = datetime.utcnow() - timedelta(hours=inactive_hours)

            # Get inactive sessions for logging
            inactive_sessions_result = await db.execute(
                select(Session).where(
                    Session.last_activity < inactive_threshold,
                    Session.is_active == True,
                )
            )
            inactive_sessions = inactive_sessions_result.scalars().all()

            # Log inactive sessions for security monitoring
            for session in inactive_sessions:
                logger.info(
                    f"Cleaning up inactive session",
                    extra={
                        "event_type": "session_inactive_cleanup",
                        "username": session.username,
                        "session_id": (
                            session.id[:8] + "..."
                            if len(session.id) > 8
                            else session.id
                        ),
                        "last_activity": (
                            session.last_activity.isoformat()
                            if session.last_activity
                            else "never"
                        ),
                        "inactive_hours": inactive_hours,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )

            # Delete inactive sessions
            result = await db.execute(
                delete(Session).where(
                    Session.last_activity < inactive_threshold,
                    Session.is_active == True,
                )
            )

            await db.commit()
            cleaned_count = result.rowcount

            if cleaned_count > 0:
                logger.info(
                    f"Inactive session cleanup completed: {cleaned_count} sessions removed",
                    extra={
                        "event_type": "session_inactive_cleanup_completed",
                        "sessions_cleaned": cleaned_count,
                        "inactive_hours": inactive_hours,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )

            return cleaned_count

        except SQLAlchemyError as e:
            logger.error(f"Database error cleaning up inactive sessions: {str(e)}")
            await db.rollback()
            return 0
        except Exception as e:
            logger.error(f"Unexpected error cleaning up inactive sessions: {str(e)}")
            await db.rollback()
            return 0

    async def get_active_sessions_count(self, db: AsyncSession) -> int:
        """
        Get the count of currently active sessions.

        Args:
            db: Database session

        Returns:
            int: Number of active sessions
        """
        try:
            result = await db.execute(
                select(func.count(Session.id)).where(
                    Session.is_active == True, Session.expires_at > datetime.utcnow()
                )
            )
            return result.scalar() or 0

        except SQLAlchemyError as e:
            logger.error(f"Database error getting active sessions count: {str(e)}")
            return 0
        except Exception as e:
            logger.error(f"Unexpected error getting active sessions count: {str(e)}")
            return 0

    async def get_session_security_info(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Get security information about current sessions for monitoring.

        Args:
            db: Database session

        Returns:
            Dict[str, Any]: Security information about sessions
        """
        try:
            # Count total sessions
            total_result = await db.execute(select(func.count(Session.id)))
            total_sessions = total_result.scalar() or 0

            # Count active sessions
            active_result = await db.execute(
                select(func.count(Session.id)).where(
                    Session.is_active == True, Session.expires_at > datetime.utcnow()
                )
            )
            active_sessions = active_result.scalar() or 0

            # Count expired sessions
            expired_result = await db.execute(
                select(func.count(Session.id)).where(
                    Session.expires_at <= datetime.utcnow()
                )
            )
            expired_sessions = expired_result.scalar() or 0

            # Count inactive sessions (no activity in last 24 hours)
            inactive_threshold = datetime.utcnow() - timedelta(hours=24)
            inactive_result = await db.execute(
                select(func.count(Session.id)).where(
                    Session.last_activity < inactive_threshold,
                    Session.is_active == True,
                )
            )
            inactive_sessions = inactive_result.scalar() or 0

            # Get oldest active session
            oldest_session_result = await db.execute(
                select(Session.created_at)
                .where(
                    Session.is_active == True, Session.expires_at > datetime.utcnow()
                )
                .order_by(Session.created_at.asc())
                .limit(1)
            )
            oldest_session = oldest_session_result.scalar()

            return {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "expired_sessions": expired_sessions,
                "inactive_sessions": inactive_sessions,
                "oldest_active_session": (
                    oldest_session.isoformat() if oldest_session else None
                ),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except SQLAlchemyError as e:
            logger.error(f"Database error getting session security info: {str(e)}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
        except Exception as e:
            logger.error(f"Unexpected error getting session security info: {str(e)}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}

    def get_demo_credentials(self) -> Optional[Dict[str, str]]:
        """
        Get demo mode credentials if demo mode is enabled.

        Returns:
            Optional[Dict[str, str]]: Demo credentials or None
        """
        if self.settings.DEMO_MODE:
            return {
                "username": self.settings.AUTH_USER,
                "password": self.settings.AUTH_PASSWORD,
            }
        return None


# Global authentication service instance
auth_service = AuthService()
