"""
Standardized error response schemas for the Cointainr API.

This module defines Pydantic models for consistent error responses
across all API endpoints.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Detailed information about an error."""

    loc: Optional[List[str]] = Field(None, description="Location of the error")
    msg: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")


class ErrorResponse(BaseModel):
    """Standard error response model."""

    error: bool = Field(True, description="Always true for error responses")
    message: str = Field(..., description="Human-readable error message")
    category: str = Field(..., description="Error category for classification")
    status_code: int = Field(..., description="HTTP status code")
    timestamp: datetime = Field(..., description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )


class ValidationErrorResponse(ErrorResponse):
    """Validation error response model."""

    validation_errors: List[ErrorDetail] = Field(
        ..., description="List of validation errors"
    )


class ExternalAPIErrorResponse(ErrorResponse):
    """External API error response model."""

    service: str = Field(..., description="External service name")
    operation: str = Field(..., description="Operation being performed")
    retry_after: Optional[int] = Field(
        None, description="Seconds to wait before retrying"
    )
    cache_fallback_available: bool = Field(
        False, description="Whether cache fallback is available"
    )


class DatabaseErrorResponse(ErrorResponse):
    """Database error response model."""

    operation: Optional[str] = Field(None, description="Database operation")
    entity: Optional[str] = Field(None, description="Entity being operated on")


class CacheErrorResponse(ErrorResponse):
    """Cache error response model."""

    cache_type: str = Field(..., description="Type of cache (price, conversion)")
    operation: str = Field(..., description="Cache operation being performed")
