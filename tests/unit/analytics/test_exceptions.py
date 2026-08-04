"""Tests for analytics-layer exceptions."""

import pytest

from lifelenz.analytics import (
    AnalyticsError,
    AnalyticsValidationError,
    InsufficientBaselineDataError,
    InsufficientTrendDataError,
)
from lifelenz.application import ApplicationError
from lifelenz.domain import DomainValidationError
from lifelenz.repositories import RepositoryError


@pytest.mark.parametrize(
    "exception_type",
    [AnalyticsValidationError, InsufficientBaselineDataError, InsufficientTrendDataError],
)
def test_specific_exceptions_derive_from_analytics_error(exception_type: type[Exception]) -> None:
    assert issubclass(exception_type, AnalyticsError)


def test_analytics_error_derives_directly_from_exception() -> None:
    assert AnalyticsError.__bases__ == (Exception,)


@pytest.mark.parametrize(
    "foreign_base",
    [ApplicationError, DomainValidationError, RepositoryError],
)
def test_analytics_errors_are_independent_of_other_layers(foreign_base: type[Exception]) -> None:
    assert not issubclass(AnalyticsError, foreign_base)


@pytest.mark.parametrize(
    "exception_type",
    [
        AnalyticsError,
        AnalyticsValidationError,
        InsufficientBaselineDataError,
        InsufficientTrendDataError,
    ],
)
def test_custom_messages_are_preserved_and_catchable(exception_type: type[AnalyticsError]) -> None:
    error = exception_type("analytics context")

    assert str(error) == "analytics context"
    with pytest.raises(AnalyticsError, match="analytics context"):
        raise error


@pytest.mark.parametrize(
    "error",
    [AnalyticsValidationError("invalid"), InsufficientTrendDataError("insufficient")],
)
def test_exceptions_do_not_add_provider_or_transport_attributes(error: AnalyticsError) -> None:
    for attribute in ("status_code", "http_status", "provider", "retry_after", "severity"):
        assert not hasattr(error, attribute)


def test_trend_insufficiency_is_distinct_from_validation_and_baseline_insufficiency() -> None:
    assert not issubclass(InsufficientTrendDataError, AnalyticsValidationError)
    assert not issubclass(InsufficientTrendDataError, InsufficientBaselineDataError)
    assert not issubclass(InsufficientBaselineDataError, InsufficientTrendDataError)
