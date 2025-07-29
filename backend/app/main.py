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
from app.core.config import settings
from app.core.error_handling import setup_exception_handlers
from app.core.logging_config import configure_logging
from app.middleware.error_logging import ErrorLoggingMiddleware
from app.middleware.auth_middleware import AuthenticationMiddleware

from app.api.endpoints import assets
from app.api.endpoints import price
from app.api.endpoints import auth
from app.services.scheduled_tasks import scheduled_task_manager
from app.services.demo_service import demo_service

# Import models to ensure they are registered with SQLAlchemy
from app.models import asset
from app.models import price_cache
from app.models import session

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
    # Startup: Validate environment, create database tables, optimize database, and start scheduled tasks
    try:
        logger.info("Starting application...")

        # Validate environment configuration
        if not settings.validate_environment():
            logger.error(
                "Environment validation failed. Check configuration and API keys."
            )
            # In production, you might want to raise an exception here
            # raise RuntimeError("Invalid environment configuration")
        else:
            logger.info(f"Environment validation passed for: {settings.ENVIRONMENT}")

        async with engine.begin() as conn:
            await conn.run_sync(metadata.create_all)
            logger.info("Database tables created successfully")

            # Log authentication table creation
            from app.core.auth_config import auth_settings

            if auth_settings.auth_enabled:
                logger.info("Authentication session table created and ready")

        # Apply database optimizations
        from app.db.optimizations import optimize_database

        await optimize_database()
        logger.info("Database optimization completed")

        # Initialize authentication system
        from app.core.auth_config import auth_settings

        if auth_settings.auth_enabled:
            logger.info(
                f"Authentication system initialized - Demo mode: {auth_settings.DEMO_MODE}"
            )
            if auth_settings.DEMO_MODE:
                logger.info("Demo credentials: username='demo', password='demo1'")
        else:
            logger.info("Authentication system disabled")

        # Initialize demo mode if enabled
        await demo_service.initialize_demo_mode()
        await demo_service.ensure_demo_asset_exists()
        logger.info("Demo mode initialization completed")

        # Start scheduled tasks
        await scheduled_task_manager.start_scheduled_tasks()
        logger.info("Scheduled tasks started successfully")
    except Exception as e:
        logger.error(f"Error during application startup: {e}", exc_info=True)
        raise

    yield

    # Shutdown: Stop scheduled tasks and demo service
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
    # Configure API documentation based on environment
    docs_url = "/docs" if settings.ENABLE_API_DOCS else None
    redoc_url = "/redoc" if settings.ENABLE_API_DOCS else None
    openapi_url = "/openapi.json" if settings.ENABLE_API_DOCS else None

    if not settings.ENABLE_API_DOCS:
        logger.info("API documentation disabled for production environment")

    app = FastAPI(
        title="Cointainr API",
        description="API for the Cointainr portfolio tracking application",
        version="1.0.0",
        lifespan=lifespan,
        # Configure documentation URLs based on environment
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
    )

    # Add error logging middleware
    app.add_middleware(ErrorLoggingMiddleware)

    # Add authentication middleware conditionally (before performance monitoring)
    from app.core.auth_config import auth_settings

    if auth_settings.auth_enabled:
        app.add_middleware(AuthenticationMiddleware)
        logger.info("Authentication middleware enabled")
    else:
        logger.info("Authentication middleware disabled")

    # Add performance monitoring middleware
    from app.core.performance_monitoring import PerformanceMonitoringMiddleware

    app.add_middleware(PerformanceMonitoringMiddleware)

    # CORS Configuration
    if settings.ENVIRONMENT == "development":
        # Development: Allow Vite dev server on different port
        dev_origins = [
            "http://localhost:5173",  # Vite dev server
            "http://127.0.0.1:5173",
            "http://localhost:8000",  # FastAPI dev server
            "http://127.0.0.1:8000",
        ]

        app.add_middleware(
            CORSMiddleware,
            allow_origins=dev_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )
        logger.info(f"CORS enabled for development with origins: {dev_origins}")
    else:
        logger.info("CORS disabled for production - using same-origin serving")

    # Set up exception handlers
    setup_exception_handlers(app)

    # Register API endpoints - ORDER MATTERS: Register all API routes before frontend handler

    # Register asset endpoints under /api/v1/assets
    app.include_router(assets.router, prefix="/api/v1/assets", tags=["assets"])

    # Register price endpoints under /api/v1/price
    app.include_router(price.router, prefix="/api/v1/price", tags=["price"])

    # Register authentication endpoints under /api/v1/auth
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])

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
