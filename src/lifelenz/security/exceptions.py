"""Technology-neutral security adapter failures."""


class SecurityError(Exception):
    """Base exception for security adapter failures."""


class TokenValidationError(SecurityError):
    """Raised when an access token cannot be trusted."""


class PasswordHashError(SecurityError):
    """Raised when a stored password hash is malformed or unsupported."""
