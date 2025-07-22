from contextlib import asynccontextmanager
import logging
import os
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pathlib

from app.db.session import engine, Base
from app.core.error_handling import setup_exception_handlers
from app.core.logging_config import configure_logging
from app.middleware.error_logging import ErrorLoggingMiddleware

from app.api.endpoints import assets
from app.api.endpoints import price
from app.api.endpoints import cache
from app.api.endpoints import conversion
from app.api.endpoints import health
from app.api.endpoints import performance
from app.services.scheduled_tasks import scheduled_task_manager

# Import models to ensure they are registered with SQLAlchemy
from app.models import asset
from app.models import price_cache
from app.models import conversion_cache

# Configure logging
log_level = os.environ.get("LOG_LEVEL", "INFO")
enable_json_logging = os.environ.get("ENABLE_JSON_LOGGING", "false").lower() == "true"
log_file = os.environ.get("LOG_FILE")
configure_logging(log_level, enable_json_logging, log_file)

# Set up logger
logger = logging.getLogger(__name__)

metadata = Base.metadata


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    Handles startup and shutdown events.
    """
    # Startup: Create database tables, optimize database, and start scheduled tasks
    try:
        logger.info("Starting application...")
        async with engine.begin() as conn:
            await conn.run_sync(metadata.create_all)
            logger.info("Database tables created successfully")

        # Apply database optimizations
        from app.db.optimizations import optimize_database

        optimized_session = await optimize_database()
        if optimized_session:
            logger.info("Using optimized database session configuration")
            # If we have an optimized session, we could replace the default session here
            # This is commented out as it would require updating all dependencies
            # from app.db.database import set_session_maker
            # set_session_maker(optimized_session)

        # Start scheduled tasks
        await scheduled_task_manager.start_scheduled_tasks()
        logger.info("Scheduled tasks started successfully")
    except Exception as e:
        logger.error(f"Error during application startup: {e}", exc_info=True)
        raise

    yield

    # Shutdown: Stop scheduled tasks
    try:
        logger.info("Shutting down application...")
        await scheduled_task_manager.stop_scheduled_tasks()
        logger.info("Scheduled tasks stopped successfully")
    except Exception as e:
        logger.error(f"Error during application shutdown: {e}", exc_info=True)


def create_app() -> FastAPI:
    """
    Application factory for FastAPI app.
    Configures middleware, routers, and events.
    """
    app = FastAPI(
        title="Cointainr API",
        description="API for the Cointainr portfolio tracking application",
        version="1.0.0",
        lifespan=lifespan,
        # Disable OpenAPI docs at /docs and /redoc to avoid conflicts with frontend routes
        # We'll serve them at custom paths
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # List of allowed origins for CORS (e.g., frontend address)
    origins = [
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8893",
        "http://127.0.0.1:8893",
        "*",  # Allow all origins when running in Docker
    ]

    # Add error logging middleware
    app.add_middleware(ErrorLoggingMiddleware)

    # Add performance monitoring middleware
    from app.core.performance_monitoring import PerformanceMonitoringMiddleware

    app.add_middleware(PerformanceMonitoringMiddleware)

    # Add CORS middleware to allow cross-origin requests
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],  # Allow all HTTP methods
        allow_headers=["*"],  # Allow all headers
    )

    # Set up exception handlers
    setup_exception_handlers(app)

    # Register API endpoints - ORDER MATTERS: Register all API routes before frontend handler

    # Register asset endpoints under /api/v1/assets
    app.include_router(assets.router, prefix="/api/v1/assets", tags=["assets"])

    # Register price endpoints under /api/v1/price
    app.include_router(price.router, prefix="/api/v1/price", tags=["price"])

    # Register cache endpoints under /api/v1/cache
    app.include_router(cache.router, prefix="/api/v1/cache", tags=["cache"])

    # Register conversion endpoints under /api/v1/conversion
    app.include_router(
        conversion.router, prefix="/api/v1/conversion", tags=["conversion"]
    )

    # Register health check endpoints under /api/v1/health
    app.include_router(health.router, prefix="/api/v1/health", tags=["health"])

    # Register performance monitoring endpoints under /api/v1/performance
    app.include_router(
        performance.router, prefix="/api/v1/performance", tags=["performance"]
    )

    # Simple health check endpoint for quick testing
    @app.get("/api/health", tags=["health"])
    def health_check():
        """Simple health check endpoint"""
        return {"status": "ok", "message": "API is running"}

    # IMPORTANT: Frontend handler must be set up AFTER all API routes
    # This ensures API routes take precedence over the catch-all frontend route
    from app.frontend import setup_frontend

    setup_frontend(app)

    return app


# App instance for ASGI servers
app = create_app()
