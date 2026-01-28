"""
TrustVault Authentication Middleware
API Key authentication and rate limiting
"""

import time
import secrets
import hashlib
import asyncio
import structlog
from typing import Optional, Dict, List
from functools import lru_cache
from fastapi import HTTPException, Header, Request, Depends

from app.config import get_settings, Settings

logger = structlog.get_logger(__name__)


# Rate limiting storage for failed auth attempts
_failed_auth_attempts: Dict[str, List[float]] = {}
MAX_AUTH_ATTEMPTS = 5
AUTH_ATTEMPT_WINDOW = 300  # 5 minutes


@lru_cache(maxsize=1000)
def hash_key(key: str) -> str:
    """Hash API key using SHA256 for constant-time comparison"""
    return hashlib.sha256(key.encode('utf-8')).hexdigest()


def get_api_key_from_header(x_api_key: Optional[str] = Header(None)) -> Optional[str]:
    """Extract API key from header"""
    return x_api_key


async def check_rate_limit(ip: str) -> bool:
    """Check if IP has exceeded auth rate limit"""
    now = time.time()

    if ip not in _failed_auth_attempts:
        _failed_auth_attempts[ip] = []

    # Remove old attempts outside the time window
    _failed_auth_attempts[ip] = [
        timestamp for timestamp in _failed_auth_attempts[ip]
        if now - timestamp < AUTH_ATTEMPT_WINDOW
    ]

    return len(_failed_auth_attempts[ip]) >= MAX_AUTH_ATTEMPTS


def record_failed_auth(ip: str):
    """Record failed authentication attempt"""
    if ip not in _failed_auth_attempts:
        _failed_auth_attempts[ip] = []
    _failed_auth_attempts[ip].append(time.time())


async def verify_api_key(
    request: Request,
    api_key: Optional[str] = Depends(get_api_key_from_header),
    settings: Settings = Depends(get_settings)
):
    """
    Verify API key with constant-time comparison and rate limiting.

    Security features:
    - Constant-time comparison to prevent timing attacks
    - Rate limiting to prevent brute force
    - Request logging for audit trail
    """
    client_ip = request.client.host if request.client else "unknown"

    # Check rate limit
    if await check_rate_limit(client_ip):
        logger.warning(
            "auth.rate_limit_exceeded",
            ip=client_ip,
            attempts=len(_failed_auth_attempts.get(client_ip, []))
        )
        raise HTTPException(
            status_code=429,
            detail="Too many authentication attempts. Try again later."
        )

    # Require API key to be configured
    if not settings.api_key or settings.api_key == "":
        logger.error("auth.not_configured")
        raise HTTPException(
            status_code=500,
            detail="Authentication not configured"
        )

    # Require API key in request
    if not api_key or api_key == "":
        record_failed_auth(client_ip)
        logger.warning("auth.missing_key", ip=client_ip)
        await asyncio.sleep(1)  # Rate limit failed attempts
        raise HTTPException(
            status_code=401,
            detail="API key required. Include X-API-Key header."
        )

    # Constant-time comparison to prevent timing attacks
    expected_hash = hash_key(settings.api_key)
    provided_hash = hash_key(api_key)

    if not secrets.compare_digest(expected_hash, provided_hash):
        record_failed_auth(client_ip)
        logger.warning(
            "auth.invalid_key",
            ip=client_ip,
            attempts=len(_failed_auth_attempts.get(client_ip, []))
        )
        await asyncio.sleep(1)  # Prevent timing attacks
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )

    # Clear failed attempts on successful authentication
    if client_ip in _failed_auth_attempts:
        _failed_auth_attempts[client_ip] = []

    # Log successful auth (for audit)
    logger.info(
        "auth.success",
        ip=client_ip,
        endpoint=str(request.url.path)
    )
