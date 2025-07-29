import os
import secrets
import logging
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class AuthSettings:
    """
    Authentication configuration class that handles environment variable loading
    and validation for the authentication system.
    """

    def __init__(self):
        # Environment settings
        self.ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production").lower()

        # Core authentication settings
        self.AUTH_USER: Optional[str] = os.getenv("AUTH_USER")
        self.AUTH_PASSWORD: Optional[str] = os.getenv("AUTH_PASSWORD")

        # Demo mode settings
        self.DEMO_MODE: bool = os.getenv("DEMO_MODE", "false").lower() in (
            "true",
            "1",
            "yes",
        )

        # Session management settings
        self.SESSION_SECRET_KEY: str = os.getenv(
            "SESSION_SECRET_KEY", secrets.token_urlsafe(32)
        )
        self.SESSION_TIMEOUT_HOURS: int = int(os.getenv("SESSION_TIMEOUT_HOURS", "24"))

        # Demo mode cleanup settings
        self.DEMO_CLEANUP_TIME: str = os.getenv("DEMO_CLEANUP_TIME", "00:00")
        self.DEMO_PRESERVE_ASSET_ID: int = int(os.getenv("DEMO_PRESERVE_ASSET_ID", "1"))

        # Set demo credentials if demo mode is enabled
        if self.DEMO_MODE:
            self.AUTH_USER = "demo"
            self.AUTH_PASSWORD = "demo1"

    @property
    def auth_enabled(self) -> bool:
        """
        Check if authentication is enabled based on environment variables.
        Authentication is enabled if AUTH_USER and AUTH_PASSWORD are set,
        or if DEMO_MODE is enabled.
        """
        return bool((self.AUTH_USER and self.AUTH_PASSWORD) or self.DEMO_MODE)

    def validate_configuration(self) -> bool:
        """
        Validate authentication configuration and log any issues.
        Returns True if configuration is valid, False otherwise.
        """
        valid = True

        # Validate session timeout
        if self.SESSION_TIMEOUT_HOURS < 1:
            logger.warning(
                f"SESSION_TIMEOUT_HOURS ({self.SESSION_TIMEOUT_HOURS}) should be at least 1. Using default: 24"
            )
            self.SESSION_TIMEOUT_HOURS = 24

        # Validate demo cleanup time format
        if self.DEMO_MODE:
            try:
                hours, minutes = self.DEMO_CLEANUP_TIME.split(":")
                if not (0 <= int(hours) <= 23 and 0 <= int(minutes) <= 59):
                    raise ValueError("Invalid time range")
            except (ValueError, IndexError):
                logger.warning(
                    f"Invalid DEMO_CLEANUP_TIME format: {self.DEMO_CLEANUP_TIME}. Using default: 00:00"
                )
                self.DEMO_CLEANUP_TIME = "00:00"

        # Validate preserve asset ID
        if self.DEMO_PRESERVE_ASSET_ID < 1:
            logger.warning(
                f"DEMO_PRESERVE_ASSET_ID ({self.DEMO_PRESERVE_ASSET_ID}) should be at least 1. Using default: 1"
            )
            self.DEMO_PRESERVE_ASSET_ID = 1

        # Log authentication status
        if self.auth_enabled:
            if self.DEMO_MODE:
                logger.info("Authentication enabled in demo mode")
            else:
                logger.info("Authentication enabled with custom credentials")
        else:
            logger.info("Authentication disabled")

        return valid


# Global authentication settings instance
auth_settings = AuthSettings()
