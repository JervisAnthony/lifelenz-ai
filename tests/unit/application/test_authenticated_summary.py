from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from lifelenz.analytics import PersonalBaseline
from lifelenz.application import (
    ApplicationValidationError,
    AuthenticatedProfileService,
    AuthenticatedWellnessSummaryService,
    MetricWellnessSummary,
    WellnessSummary,
    WellnessSummaryService,
    WellnessSummaryUnavailableError,
)
from lifelenz.domain import (
    MeasurementUnit,
    MetricIdentifier,
    ProfileId,
    TimeRange,
    WellnessProfile,
)
from lifelenz.identity import UserId


def summary() -> WellnessSummary:
    profile = WellnessProfile(ProfileId.generate(), "UTC")
    observed_at = datetime(2026, 1, 1, tzinfo=UTC)
    baseline = PersonalBaseline(
        profile.profile_id,
        MetricIdentifier.WATER_INTAKE,
        MeasurementUnit.MILLILITERS,
        1,
        250.0,
        250.0,
        250,
        250,
        0.0,
        observed_at,
        observed_at,
        None,
    )
    return WellnessSummary(
        profile,
        (
            MetricWellnessSummary(
                MetricIdentifier.WATER_INTAKE,
                MeasurementUnit.MILLILITERS,
                baseline,
                None,
            ),
        ),
        None,
        1,
    )


def test_authenticated_summary_delegates_range_and_projects_requested_metrics() -> None:
    profiles = Mock(spec=AuthenticatedProfileService)
    summaries = Mock(spec=WellnessSummaryService)
    service = AuthenticatedWellnessSummaryService(profiles, summaries)
    value = summary()
    user = UserId.new()
    time_range = TimeRange(
        datetime(2026, 1, 1, tzinfo=UTC),
        datetime(2026, 1, 2, tzinfo=UTC),
    )
    profiles.get_profile.return_value = value.profile
    summaries.create_summary.return_value = value

    assert service.create_summary(user) is value
    projected = service.create_summary(
        user,
        metrics=(MetricIdentifier.WATER_INTAKE,),
        time_range=time_range,
    )
    assert projected.metrics == value.metrics
    assert projected.generated_from_record_count == 1
    summaries.create_summary.assert_called_with(value.profile_id, time_range=time_range)


def test_authenticated_summary_rejects_unavailable_duplicate_and_invalid_selection() -> None:
    profiles = Mock(spec=AuthenticatedProfileService)
    summaries = Mock(spec=WellnessSummaryService)
    service = AuthenticatedWellnessSummaryService(profiles, summaries)
    value = summary()
    user = UserId.new()
    profiles.get_profile.return_value = value.profile
    summaries.create_summary.return_value = value

    with pytest.raises(WellnessSummaryUnavailableError):
        service.create_summary(user, metrics=(MetricIdentifier.STEPS,))
    with pytest.raises(ApplicationValidationError):
        service.create_summary(
            user,
            metrics=(MetricIdentifier.STEPS, MetricIdentifier.STEPS),
        )
    with pytest.raises(ApplicationValidationError):
        service.create_summary(user, metrics=[MetricIdentifier.STEPS])  # type: ignore[arg-type]
    with pytest.raises(ApplicationValidationError):
        service.create_summary(user, metrics=("steps",))  # type: ignore[arg-type]


def test_authenticated_summary_constructor_requires_application_services() -> None:
    profiles = Mock(spec=AuthenticatedProfileService)
    summaries = Mock(spec=WellnessSummaryService)
    with pytest.raises(ApplicationValidationError):
        AuthenticatedWellnessSummaryService(object(), summaries)  # type: ignore[arg-type]
    with pytest.raises(ApplicationValidationError):
        AuthenticatedWellnessSummaryService(profiles, object())  # type: ignore[arg-type]
