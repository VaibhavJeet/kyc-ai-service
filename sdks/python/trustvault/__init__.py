"""
TrustVault Python SDK
Official SDK for TrustVault API
"""

from .client import TrustVault, TrustVaultError
from .models import (
    FaceVerifyRequest, FaceVerifyResponse,
    KYCVerifyRequest, KYCVerifyResponse,
    TrustScoreRequest, TrustScoreResponse,
    BusinessVerifyRequest, BusinessVerifyResponse,
)

__version__ = "1.0.0"
__all__ = [
    "TrustVault",
    "TrustVaultError",
    "FaceVerifyRequest",
    "FaceVerifyResponse", 
    "KYCVerifyRequest",
    "KYCVerifyResponse",
    "TrustScoreRequest",
    "TrustScoreResponse",
    "BusinessVerifyRequest",
    "BusinessVerifyResponse",
]
