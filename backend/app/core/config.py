import os
from dotenv import load_dotenv

load_dotenv()  # Loads variables from .env


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    FINNHUB_API_KEY: str = os.getenv("FINNHUB_API_KEY", "")
    EXCHANGERATE_API_KEY: str = os.getenv("EXCHANGERATE_API_KEY", "")

    # Price cache settings
    PRICE_CACHE_MINUTES: int = int(os.getenv("PRICE_CACHE_MINUTES", "15"))
    PRICE_CACHE_CLEANUP_DAYS: int = int(os.getenv("PRICE_CACHE_CLEANUP_DAYS", "30"))

    # Conversion cache settings
    CONVERSION_CACHE_HOURS: int = int(os.getenv("CONVERSION_CACHE_HOURS", "24"))
    CONVERSION_CACHE_CLEANUP_DAYS: int = int(
        os.getenv("CONVERSION_CACHE_CLEANUP_DAYS", "7")
    )


settings = Settings()
