import os
from dotenv import load_dotenv

load_dotenv()  # Loads variables from .env


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    FINNHUB_API_KEY: str = os.getenv("FINNHUB_API_KEY", "")
    EXCHANGERATE_API_KEY: str = os.getenv("EXCHANGERATE_API_KEY", "")


settings = Settings()
