"""
TrustVault API v1 - Main Router
Aggregates all v1 endpoints
"""

from fastapi import APIRouter
from app.api.v1 import verify, trust, protect, health, webhook

router = APIRouter(prefix="/v1", tags=["TrustVault API v1"])

# Include all sub-routers
router.include_router(health.router, tags=["Health"])
router.include_router(verify.router, prefix="/verify", tags=["Verification"])
router.include_router(trust.router, prefix="/trust", tags=["Trust Score"])
router.include_router(protect.router, prefix="/protect", tags=["Protection"])
router.include_router(webhook.router, prefix="/webhooks", tags=["Webhooks"])
