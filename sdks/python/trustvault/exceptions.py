"""
TrustVault SDK Exceptions
"""


class TrustVaultError(Exception):
    """Base exception for TrustVault SDK"""

    def __init__(
        self,
        message: str,
        code: str = "UNKNOWN_ERROR",
        status_code: int = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)

    def __str__(self):
        if self.status_code:
            return f"[{self.code}] {self.message} (HTTP {self.status_code})"
        return f"[{self.code}] {self.message}"


class AuthenticationError(TrustVaultError):
    """Raised when API key is invalid or missing"""
    pass


class RateLimitError(TrustVaultError):
    """Raised when rate limit is exceeded"""
    pass


class ValidationError(TrustVaultError):
    """Raised when request validation fails"""
    pass
