# Multi-stage build for Cointainr application

# Stage 1: Build frontend
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package files and install dependencies
# This layer will be cached unless package files change
COPY frontend/package*.json ./
RUN npm ci

# Copy only necessary frontend source files
# Exclude node_modules, tests, and other non-build files
COPY frontend/src ./src
COPY frontend/static ./static
COPY frontend/*.js ./
COPY frontend/*.ts ./
COPY frontend/.npmrc ./
COPY frontend/.prettierrc ./
COPY frontend/.prettierignore ./

# Build the frontend
RUN npm run build

# Stage 2: Final image
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# This layer will be cached unless requirements.txt changes
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy only necessary backend code
# Exclude tests, __pycache__, and other non-runtime files
COPY backend/app ./app

# Copy built frontend from the correct build directory (SvelteKit's 'build' output)
# This is where the static adapter outputs files, which will be served by FastAPI
COPY --from=frontend-builder /app/frontend/build /app/static

# Create data directory for SQLite database and other persistent data
RUN mkdir -p /app/data && chmod 777 /app/data

# Set environment variables
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Start the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]