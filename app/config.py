"""
TrustVault Configuration
Re-exports from app.core.config for convenience
"""

# Re-export everything from core.config
# This allows imports from either:
#   from app.config import get_settings
#   from app.core.config import get_settings
from app.core.config import Settings, get_settings

__all__ = ["Settings", "get_settings"]
