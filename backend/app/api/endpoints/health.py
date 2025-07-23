"""
Health check endpoints for the Cointainr API.

These endpoints provide health status information for the API
and its dependencies.
"""

import logging
from typing import Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.database import get_db
from app.services.enhanced_price_service import enhanced_price_service
from app.utils.graceful_degradation import get_all_circuit_breakers

# Set up logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


@router.get("/health", response_model=Dict[str, Any])
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Check the health of the API and its dependencies.

    Returns:
        Dict with health status information
    """
    try:
        # Check database connection
        db_status = "healthy"
        db_error = None
        try:
            # Execute a simple query to check database connection
            result = await db.execute(text("SELECT 1"))
            result.fetchone()
        except Exception as e:
            db_status = "unhealthy"
            db_error = str(e)
            logger.error(f"Database health check failed: {e}", exc_info=True)

        # Get API stats
        api_stats = await enhanced_price_service.get_api_stats()

        # Get circuit breaker status
        circuit_breakers = get_all_circuit_breakers()

        # Check if any circuit breakers are open
        circuit_breaker_status = "healthy"
        for cb_name, cb_status in circuit_breakers.items():
            if cb_status["state"] == "open":
                circuit_breaker_status = "degraded"
                break

        # Determine overall status
        overall_status = "healthy"
        if (
            db_status != "healthy"
            or api_stats["error_rate"] > 10
            or circuit_breaker_status != "healthy"
        ):
            overall_status = "degraded"

        # Return health status
        return {
            "status": overall_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0",
            "components": {
                "database": {
                    "status": db_status,
                    "error": db_error,
                },
                "api": {
                    "status": "healthy" if api_stats["error_rate"] < 10 else "degraded",
                    "stats": api_stats,
                },
                "circuit_breakers": {
                    "status": circuit_breaker_status,
                    "breakers": circuit_breakers,
                },
            },
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}",
        )


@router.get("/health/database", response_model=Dict[str, Any])
async def database_health_check(db: AsyncSession = Depends(get_db)):
    """
    Check the health of the database.

    Returns:
        Dict with database health status information
    """
    try:
        # Check database connection
        start_time = datetime.now(timezone.utc)
        result = await db.execute(text("SELECT 1"))
        result.fetchone()
        end_time = datetime.now(timezone.utc)

        # Calculate response time
        response_time_ms = (end_time - start_time).total_seconds() * 1000

        # Return health status
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "response_time_ms": response_time_ms,
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database health check failed: {str(e)}",
        )


@router.get("/health/external-apis", response_model=Dict[str, Any])
async def external_apis_health_check():
    """
    Check the health of external APIs.

    Returns:
        Dict with external APIs health status information
    """
    try:
        # Get API stats
        api_stats = await enhanced_price_service.get_api_stats()

        # Get circuit breaker status
        circuit_breakers = get_all_circuit_breakers()

        # Check if any circuit breakers are open
        circuit_breaker_status = "healthy"
        open_breakers = []
        for cb_name, cb_status in circuit_breakers.items():
            if cb_status["state"] == "open":
                circuit_breaker_status = "degraded"
                open_breakers.append(cb_name)

        # Return health status
        return {
            "status": (
                "healthy"
                if api_stats["error_rate"] < 10 and circuit_breaker_status == "healthy"
                else "degraded"
            ),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "api_stats": api_stats,
            "circuit_breakers": {
                "status": circuit_breaker_status,
                "open_breakers": open_breakers,
                "details": circuit_breakers,
            },
        }
    except Exception as e:
        logger.error(f"External APIs health check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"External APIs health check failed: {str(e)}",
        )


@router.get("/health/circuit-breakers", response_model=Dict[str, Any])
async def circuit_breakers_status():
    """
    Get status of all circuit breakers.

    Returns:
        Dict with circuit breaker status information
    """
    try:
        # Get circuit breaker status
        circuit_breakers = get_all_circuit_breakers()

        # Check if any circuit breakers are open
        circuit_breaker_status = "healthy"
        open_breakers = []
        for cb_name, cb_status in circuit_breakers.items():
            if cb_status["state"] == "open":
                circuit_breaker_status = "degraded"
                open_breakers.append(cb_name)

        # Return circuit breaker status
        return {
            "status": circuit_breaker_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "open_breakers": open_breakers,
            "breakers": circuit_breakers,
        }
    except Exception as e:
        logger.error(f"Circuit breakers status check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Circuit breakers status check failed: {str(e)}",
        )
