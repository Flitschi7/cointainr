from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # Import the CORS middleware

from app.db.session import engine, Base
from app.api.endpoints import assets

metadata = Base.metadata

app = FastAPI(title="Cointainr API")

# Define the list of allowed origins (your frontend's address)
origins = [
    "http://localhost:5173",
]

# Add the CORS middleware to the application
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)


# Include the router for asset endpoints
app.include_router(assets.router, prefix="/api/v1/assets", tags=["assets"])


@app.on_event("startup")
async def startup_event():
    """
    On startup, create the database tables.
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
