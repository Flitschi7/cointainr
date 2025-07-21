"""
API endpoints for performance monitoring.

This module provides endpoints for accessing performance metrics
and configuring performance monitoring settings.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional

from app.db.database import get_db
from app.core.performance_monitoring import (
    get_performance_metrics,
    reset_performance_metrics,
    configure_performance_monitoring,
)

router = APIRouter()


@router.get("/metrics", response_model=Dict[str, Any])
async def get_metrics(
    include_slow: bool = Query(
        True, description="Include slow operations in the metrics"
    ),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get performance metrics for the application.

    Args:
        include_slow: Whether to include slow operations in the metrics
        db: Database session

    Returns:
        Dict containing performance metrics
    """
    metrics = get_performance_metrics()

    # Remove slow operations if not requested
    if not include_slow:
        if "api_calls" in metrics:
            metrics["api_calls"].pop("slow_operations", None)
        if "database" in metrics:
            metrics["database"].pop("slow_queries", None)

    return metrics


@router.post("/metrics/reset", response_model=Dict[str, str])
async def reset_metrics() -> Dict[str, str]:
    """
    Reset all performance metrics.

    Returns:
        Dict with status message
    """
    reset_performance_metrics()
    return {"status": "Performance metrics reset successfully"}


@router.post("/configure", response_model=Dict[str, Any])
async def configure_monitoring(
    slow_threshold_ms: Optional[int] = Query(
        None, description="Threshold for slow operations in milliseconds"
    ),
    max_metrics_history: Optional[int] = Query(
        None, description="Maximum number of metrics to store in history"
    ),
) -> Dict[str, Any]:
    """
    Configure performance monitoring settings.

    Args:
        slow_threshold_ms: Threshold for slow operations in milliseconds
        max_metrics_history: Maximum number of metrics to store in history

    Returns:
        Dict with updated configuration
    """
    # Only update provided parameters
    kwargs = {}
    if slow_threshold_ms is not None:
        kwargs["slow_threshold_ms"] = slow_threshold_ms
    if max_metrics_history is not None:
        kwargs["max_metrics_history"] = max_metrics_history

    # Apply configuration if any parameters were provided
    if kwargs:
        configure_performance_monitoring(**kwargs)

    return {
        "status": "Performance monitoring configured successfully",
        "configuration": {
            "slow_threshold_ms": slow_threshold_ms,
            "max_metrics_history": max_metrics_history,
        },
    }
