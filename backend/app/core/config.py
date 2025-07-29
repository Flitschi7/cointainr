import os
import logging
from dotenv import load_dotenv
from .auth_config import auth_settings

load_dotenv()  # Loads variables from .env

logger = logging.getLogger(__name__)


class Settings:
    # Environment settings
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production").lower()

    DATABASE_URL: str = os.getenv(
        "COINTAINR_DATABASE_URL", "sqlite+aiosqlite:///./cointainr.db"
    )
    FINNHUB_API_KEY: str = os.getenv("FINNHUB_API_KEY", "")
    EXCHANGERATE_API_KEY: str = os.getenv("EXCHANGERATE_API_KEY", "")

    # Price cache settings
    PRICE_CACHE_MINUTES: int = int(
        os.getenv("PRICE_CACHE_TTL_MINUTES", os.getenv("PRICE_CACHE_MINUTES", "15"))
    )
    PRICE_CACHE_CLEANUP_DAYS: int = int(os.getenv("PRICE_CACHE_CLEANUP_DAYS", "30"))

    # Conversion cache settings
    CONVERSION_CACHE_HOURS: int = int(
        os.getenv(
            "CONVERSION_CACHE_TTL_HOURS", os.getenv("CONVERSION_CACHE_HOURS", "24")
        )
    )
    CONVERSION_CACHE_CLEANUP_DAYS: int = int(
        os.getenv("CONVERSION_CACHE_CLEANUP_DAYS", "7")
    )

    # Default currency setting
    DEFAULT_CURRENCY: str = os.getenv("DEFAULT_CURRENCY", "USD")

    # Force refresh only mode
    FORCE_REFRESH_ONLY: bool = os.getenv("FORCE_REFRESH_ONLY", "false").lower() in (
        "true",
        "1",
        "yes",
    )

    # API Documentation settings
    ENABLE_API_DOCS: bool = os.getenv(
        "ENABLE_API_DOCS", "true" if ENVIRONMENT == "development" else "false"
    ).lower() in (
        "true",
        "1",
        "yes",
    )

    # Authentication settings (imported from auth_config)
    @property
    def auth_settings(self):
        """Access to authentication settings"""
        return auth_settings

    def validate_environment(self) -> bool:
        """
        Validate critical environment variables and configuration.
        Returns True if valid, False otherwise.
        """
        valid = True

        # Validate environment setting
        if self.ENVIRONMENT not in ["development", "production", "staging"]:
            logger.warning(
                f"Invalid ENVIRONMENT setting: {self.ENVIRONMENT}. Using 'production'"
            )
            self.ENVIRONMENT = "production"

        # Validate API keys for production
        if self.ENVIRONMENT == "production":
            if not self.FINNHUB_API_KEY:
                logger.error("FINNHUB_API_KEY is required for production environment")
                valid = False
            if not self.EXCHANGERATE_API_KEY:
                logger.error(
                    "EXCHANGERATE_API_KEY is required for production environment"
                )
                valid = False

        # Validate cache settings
        if self.PRICE_CACHE_MINUTES < 1:
            logger.warning(
                f"PRICE_CACHE_MINUTES ({self.PRICE_CACHE_MINUTES}) should be at least 1. Using default: 15"
            )
            self.PRICE_CACHE_MINUTES = 15

        if self.CONVERSION_CACHE_HOURS < 1:
            logger.warning(
                f"CONVERSION_CACHE_HOURS ({self.CONVERSION_CACHE_HOURS}) should be at least 1. Using default: 24"
            )
            self.CONVERSION_CACHE_HOURS = 24

        # Validate currency code
        if len(self.DEFAULT_CURRENCY) != 3:
            logger.warning(
                f"DEFAULT_CURRENCY should be a 3-letter currency code. Got: {self.DEFAULT_CURRENCY}. Using USD"
            )
            self.DEFAULT_CURRENCY = "USD"

        # Validate authentication settings
        auth_valid = self.auth_settings.validate_configuration()
        if not auth_valid:
            logger.warning("Authentication configuration validation failed")
            valid = False

        return valid


settings = Settings()
