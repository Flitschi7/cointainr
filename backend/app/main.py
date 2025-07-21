from contextlib import asynccontextmanager
import logging
import os
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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
    )

    # List of allowed origins for CORS (e.g., frontend address)
    origins = [
        "http://localhost:5173",
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

    # Debug endpoint to check what files exist
    @app.get("/debug/files")
    def debug_files():
        """Debug endpoint to check what files exist in the static directory"""
        static_dir = pathlib.Path("/app/static")
        files_info = {
            "static_dir_exists": static_dir.exists(),
            "static_dir_contents": [],
            "client_dir_exists": False,
            "client_dir_contents": [],
        }

        if static_dir.exists():
            try:
                files_info["static_dir_contents"] = [
                    str(f) for f in static_dir.iterdir()
                ]

                client_dir = static_dir / "client"
                if client_dir.exists():
                    files_info["client_dir_exists"] = True
                    files_info["client_dir_contents"] = [
                        str(f) for f in client_dir.rglob("*")
                    ][
                        :50
                    ]  # Limit to 50 files
            except Exception as e:
                files_info["error"] = str(e)

        return files_info

    # Mount static files from the frontend build
    static_dir = pathlib.Path("/app/static")
    client_dir = static_dir / "client"

    # Try different possible locations for the frontend files
    possible_frontend_dirs = [
        client_dir,  # /app/static/client (SvelteKit default)
        static_dir,  # /app/static (if copied directly)
        static_dir / "build",  # /app/static/build (adapter-static)
    ]

    frontend_dir = None
    for dir_path in possible_frontend_dirs:
        if dir_path.exists():
            frontend_dir = dir_path
            logger.info(f"Found frontend files in: {frontend_dir}")
            break

    if frontend_dir:
        # Mount the frontend directory for static assets
        app_assets_dir = frontend_dir / "_app"
        if app_assets_dir.exists():
            app.mount(
                "/_app", StaticFiles(directory=str(app_assets_dir)), name="static_app"
            )

        # Serve favicon and other static files
        for static_file in frontend_dir.glob("*.*"):
            if static_file.is_file() and static_file.name != "index.html":

                @app.get(f"/{static_file.name}")
                def serve_static_file(static_file=static_file):
                    return FileResponse(str(static_file))

        @app.get("/")
        def read_root():
            """
            Serve the frontend SPA
            """
            # Try to find index.html
            index_path = frontend_dir / "index.html"
            if index_path.exists():
                return FileResponse(str(index_path))

            # Fallback to API message with debug info
            return {
                "message": "Welcome to the Cointainr Backend!",
                "debug": {
                    "frontend_dir": str(frontend_dir),
                    "index_path": str(index_path),
                    "index_exists": index_path.exists(),
                    "hint": "Visit /debug/files to see what files are available",
                },
            }

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str, request: Request):
            """
            Serve SPA routes - catch all routes and return the index.html
            """
            # Skip API routes
            if full_path.startswith("api/"):
                return {"message": "API endpoint not found", "path": full_path}

            # First check if the path exists as a static file
            requested_path = frontend_dir / full_path
            if requested_path.exists() and requested_path.is_file():
                return FileResponse(str(requested_path))

            # Check in _app directory
            app_path = frontend_dir / "_app" / full_path
            if app_path.exists() and app_path.is_file():
                return FileResponse(str(app_path))

            # Otherwise return index.html for SPA routing
            index_path = frontend_dir / "index.html"
            if index_path.exists():
                return FileResponse(str(index_path))

            # Fallback
            return {
                "message": "File not found",
                "path": full_path,
                "frontend_dir": str(frontend_dir),
            }

    else:
        logger.warning("No frontend files found in any expected location")

        @app.get("/")
        def read_root():
            return {
                "message": "Welcome to the Cointainr Backend!",
                "error": "Frontend files not found",
                "checked_paths": [str(d) for d in possible_frontend_dirs],
                "hint": "Visit /debug/files to see what files are available",
            }

    return app


# App instance for ASGI servers
app = create_app()
