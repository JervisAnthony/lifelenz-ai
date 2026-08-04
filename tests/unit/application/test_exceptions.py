"""Tests for application-service exceptions."""

import pytest

from lifelenz.application import (
    ApplicationError,
    ApplicationValidationError,
    GoalNotFoundError,
    ProfileNotFoundError,
    WellnessRecordNotFoundError,
    WellnessSummaryUnavailableError,
)

APPLICATION_EXCEPTIONS = (
    ApplicationValidationError,
    ProfileNotFoundError,
    GoalNotFoundError,
    WellnessRecordNotFoundError,
    WellnessSummaryUnavailableError,
)


def test_application_error_derives_from_exception() -> None:
    assert issubclass(ApplicationError, Exception)


@pytest.mark.parametrize("exception_type", APPLICATION_EXCEPTIONS)
def test_specific_exceptions_derive_from_application_error(
    exception_type: type[ApplicationError],
) -> None:
    assert issubclass(exception_type, ApplicationError)


@pytest.mark.parametrize("exception_type", (ApplicationError, *APPLICATION_EXCEPTIONS))
def test_application_exception_preserves_custom_message(
    exception_type: type[ApplicationError],
) -> None:
    error = exception_type("synthetic entity identifier")

    assert str(error) == "synthetic entity identifier"


@pytest.mark.parametrize("exception_type", APPLICATION_EXCEPTIONS)
def test_specific_exceptions_are_catchable_through_base(
    exception_type: type[ApplicationError],
) -> None:
    with pytest.raises(ApplicationError, match="synthetic"):
        raise exception_type("synthetic")


@pytest.mark.parametrize("exception_type", (ApplicationError, *APPLICATION_EXCEPTIONS))
def test_application_exceptions_have_no_provider_or_http_metadata(
    exception_type: type[ApplicationError],
) -> None:
    error = exception_type("synthetic")

    assert not hasattr(error, "http_status")
    assert not hasattr(error, "provider")
    assert not hasattr(error, "retry_after")


def test_summary_unavailable_is_distinct_from_validation_and_not_found_errors() -> None:
    assert WellnessSummaryUnavailableError.__bases__ == (ApplicationError,)
    assert not issubclass(WellnessSummaryUnavailableError, ApplicationValidationError)
    assert not issubclass(WellnessSummaryUnavailableError, ProfileNotFoundError)
    assert not issubclass(WellnessSummaryUnavailableError, WellnessRecordNotFoundError)
    error = WellnessSummaryUnavailableError("no observations")
    assert not hasattr(error, "severity")
    assert not hasattr(error, "logger")
