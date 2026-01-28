"""
TrustVault Common Schemas
Shared Pydantic models used across endpoints
"""

from typing import Optional, Any, Dict
from pydantic import BaseModel


class BaseResponse(BaseModel):
    """Base response model with success/error tracking"""
    success: bool = True
    error: Optional[str] = None
    error_code: Optional[str] = None


class PaginatedResponse(BaseModel):
    """Paginated response wrapper"""
    data: list
    total: int
    page: int
    page_size: int
    has_more: bool


class ErrorResponse(BaseModel):
    """Standard error response"""
    success: bool = False
    error: str
    error_code: str
    details: Optional[Dict[str, Any]] = None
