"""Expected failures raised by deterministic wellness analytics."""


class AnalyticsError(Exception):
    """Base exception for expected analytics-layer failures."""


class AnalyticsValidationError(AnalyticsError):
    """Raised when an analytics argument violates its public contract."""


class InsufficientBaselineDataError(AnalyticsError):
    """Raised when filtering leaves no samples for a requested baseline."""


class InsufficientTrendDataError(AnalyticsError):
    """Raised when fewer than two samples remain for a requested trend."""
