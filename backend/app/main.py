from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.session import engine, Base

from app.api.endpoints import assets
from app.api.endpoints import price

# Import models to ensure they are registered with SQLAlchemy
from app.models import asset
from app.models import price_cache
from app.models import conversion_cache

metadata = Base.metadata


def create_app() -> FastAPI:
    """
    Application factory for FastAPI app.
    Configures middleware, routers, and events.
    """
    app = FastAPI(title="Cointainr API")

    # List of allowed origins for CORS (e.g., frontend address)
    origins = [
        "http://localhost:5173",
    ]

    # Add CORS middleware to allow cross-origin requests
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],  # Allow all HTTP methods
        allow_headers=["*"],  # Allow all headers
    )

    # Register asset endpoints under /api/v1/assets
    app.include_router(assets.router, prefix="/api/v1/assets", tags=["assets"])
    # Register price endpoints under /api/v1/price
    app.include_router(price.router, prefix="/api/v1/price", tags=["price"])

    @app.on_event("startup")
    async def startup_event():
        """
        On application startup, create database tables if they do not exist.
        """
        async with engine.begin() as conn:
            await conn.run_sync(metadata.create_all)

    @app.get("/")
    def read_root():
        """
        Root endpoint for the Cointainr API.
        Returns a welcome message.
        """
        return {"message": "Welcome to the Cointainr Backend!"}

    return app


# App instance for ASGI servers
app = create_app()
