"""
Static file handler for serving the SvelteKit frontend.
"""

import pathlib
import logging
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)


def setup_static_routes(app: FastAPI):
    """
    Set up routes for serving static files from the SvelteKit frontend.
    """
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

    if not frontend_dir:
        logger.warning("No frontend files found in any expected location")

        @app.get("/")
        def read_root():
            return {
                "message": "Welcome to the Cointainr Backend!",
                "error": "Frontend files not found",
                "checked_paths": [str(d) for d in possible_frontend_dirs],
            }

        return

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

    # Debug endpoint to examine JS files
    @app.get("/debug/js")
    def debug_js():
        """Debug endpoint to examine JavaScript files"""
        js_info = {"entry_files": [], "js_content": {}}

        try:
            # Find entry JS files
            entry_dir = frontend_dir / "_app" / "immutable" / "entry"
            if entry_dir.exists():
                js_info["entry_files"] = [str(f) for f in entry_dir.glob("*.js")]

                # Read the first few lines of each file to see exports
                for js_file in entry_dir.glob("*.js"):
                    try:
                        with open(js_file, "r") as f:
                            content = f.read(500)  # Read first 500 chars
                            js_info["js_content"][str(js_file)] = content
                    except Exception as e:
                        js_info["js_content"][
                            str(js_file)
                        ] = f"Error reading file: {str(e)}"
        except Exception as e:
            js_info["error"] = str(e)

        return js_info

    # Create a simple HTML file that loads the SvelteKit app
    @app.get("/")
    def read_root():
        """Serve the frontend SPA"""
        # Try to find index.html
        index_path = frontend_dir / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))

        # Redirect to the API docs directly
        from fastapi.responses import RedirectResponse

        return RedirectResponse(url="/docs")

    # Register the API docs route explicitly
    @app.get("/docs", include_in_schema=False)
    async def get_swagger_docs():
        """Redirect to the Swagger UI docs"""
        from fastapi.responses import RedirectResponse

        return RedirectResponse(url="/api/v1/docs")

    # Catch-all route for SPA - this should be the LAST route registered
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str, request: Request):
        """Serve SPA routes"""
        # Skip API routes - don't handle them here
        if full_path.startswith("api/"):
            # Let the request continue to the API handlers
            return None

        # Special case for docs
        if full_path == "docs":
            from fastapi.responses import RedirectResponse

            return RedirectResponse(url="/api/v1/docs")

        # First check if the path exists as a static file
        requested_path = frontend_dir / full_path
        if requested_path.exists() and requested_path.is_file():
            return FileResponse(str(requested_path))

        # Check in _app directory
        app_path = frontend_dir / "_app" / full_path
        if app_path.exists() and app_path.is_file():
            return FileResponse(str(app_path))

        # Otherwise redirect to API docs
        from fastapi.responses import RedirectResponse

        return RedirectResponse(url="/docs")
