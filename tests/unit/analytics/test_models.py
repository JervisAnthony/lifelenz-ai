"""Tests for immutable analytics values."""

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime, timedelta, tzinfo
from enum import Enum
from math import inf, nan

import pytest

from lifelenz.analytics import AnalyticsValidationError, MetricSample, PersonalBaseline
from lifelenz.domain import MeasurementUnit, MetricIdentifier, ProfileId, RecordId, TimeRange
from lifelenz.domain.taxonomy import DEFAULT_UNIT_BY_METRIC

PROFILE_ID = ProfileId("00000000-0000-4000-8000-000000000001")
RECORD_ID = RecordId("sample-1")
OBSERVED_AT = datetime(2026, 1, 2, 8, 30, tzinfo=UTC)


class UnrelatedEnum(Enum):
    VALUE = "value"


class MissingOffsetTimezone(tzinfo):
    def utcoffset(self, dt: datetime | None) -> None:
        return None

    def dst(self, dt: datetime | None) -> None:
        return None


class BrokenTimezone(tzinfo):
    def utcoffset(self, dt: datetime | None) -> timedelta:
        raise ValueError("broken timezone")

    def dst(self, dt: datetime | None) -> None:
        return None


def make_sample(**overrides: object) -> MetricSample:
    values = {
        "profile_id": PROFILE_ID,
        "metric": MetricIdentifier.STEPS,
        "value": 42,
        "unit": MeasurementUnit.COUNT,
        "observed_at": OBSERVED_AT,
        "source_record_id": RECORD_ID,
    }
    values.update(overrides)
    return MetricSample(**values)  # type: ignore[arg-type]


def make_baseline(**overrides: object) -> PersonalBaseline:
    values = {
        "profile_id": PROFILE_ID,
        "metric": MetricIdentifier.STEPS,
        "unit": MeasurementUnit.COUNT,
        "sample_count": 2,
        "mean": 15.0,
        "median": 15.0,
        "minimum": 10,
        "maximum": 20,
        "population_standard_deviation": 5.0,
        "first_observed_at": OBSERVED_AT,
        "last_observed_at": OBSERVED_AT + timedelta(days=2),
        "time_range": None,
    }
    values.update(overrides)
    return PersonalBaseline(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [0, -2, 3, 4.5, 10**1000])
def test_metric_sample_preserves_plain_finite_numeric_values(value: int | float) -> None:
    sample = make_sample(value=value)

    assert sample.value == value
    assert type(sample.value) is type(value)
    assert sample.profile_id is PROFILE_ID
    assert sample.metric is MetricIdentifier.STEPS
    assert sample.unit is MeasurementUnit.COUNT
    assert sample.observed_at is OBSERVED_AT
    assert sample.source_record_id is RECORD_ID


def test_metric_sample_has_value_equality_hashability_and_immutability() -> None:
    sample = make_sample()

    assert sample == make_sample()
    assert hash(sample) == hash(make_sample())
    with pytest.raises((FrozenInstanceError, AttributeError)):
        sample.value = 9  # type: ignore[misc]


@pytest.mark.parametrize(
    ("metric", "unit"),
    list(DEFAULT_UNIT_BY_METRIC.items()),
)
def test_metric_sample_accepts_every_taxonomy_canonical_unit(
    metric: MetricIdentifier,
    unit: MeasurementUnit,
) -> None:
    assert make_sample(metric=metric, unit=unit).unit is unit


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("profile_id", PROFILE_ID.value),
        ("profile_id", RECORD_ID),
        ("metric", MetricIdentifier.STEPS.value),
        ("metric", UnrelatedEnum.VALUE),
        ("unit", MeasurementUnit.COUNT.value),
        ("unit", UnrelatedEnum.VALUE),
        ("source_record_id", RECORD_ID.value),
        ("source_record_id", PROFILE_ID),
    ],
)
def test_metric_sample_rejects_untyped_identifiers_taxonomy_and_units(
    field: str,
    value: object,
) -> None:
    with pytest.raises(AnalyticsValidationError, match=field):
        make_sample(**{field: value})


@pytest.mark.parametrize("value", [True, False, "3", None, nan, inf, -inf, {}, [], ()])
def test_metric_sample_rejects_invalid_numeric_values(value: object) -> None:
    with pytest.raises(AnalyticsValidationError, match="value"):
        make_sample(value=value)


def test_metric_sample_rejects_noncanonical_unit() -> None:
    with pytest.raises(AnalyticsValidationError, match="unit must be 'count'"):
        make_sample(unit=MeasurementUnit.KILOMETERS)


@pytest.mark.parametrize(
    "observed_at",
    [date(2026, 1, 2), "2026-01-02", None, datetime(2026, 1, 2), {}],
)
def test_metric_sample_rejects_invalid_or_naive_timestamps(observed_at: object) -> None:
    with pytest.raises(AnalyticsValidationError, match="observed_at"):
        make_sample(observed_at=observed_at)


@pytest.mark.parametrize("timezone", [MissingOffsetTimezone(), BrokenTimezone()])
def test_metric_sample_rejects_unusable_timezone_offsets(timezone: tzinfo) -> None:
    with pytest.raises(AnalyticsValidationError, match="observed_at"):
        make_sample(observed_at=datetime(2026, 1, 2, tzinfo=timezone))


def test_personal_baseline_preserves_valid_fields_and_is_immutable() -> None:
    time_range = TimeRange(OBSERVED_AT, OBSERVED_AT + timedelta(days=3))
    baseline = make_baseline(time_range=time_range)

    assert baseline.profile_id is PROFILE_ID
    assert baseline.metric is MetricIdentifier.STEPS
    assert baseline.unit is MeasurementUnit.COUNT
    assert baseline.sample_count == 2
    assert baseline.mean == 15.0
    assert baseline.median == 15.0
    assert baseline.minimum == 10
    assert baseline.maximum == 20
    assert baseline.population_standard_deviation == 5.0
    assert baseline.time_range is time_range
    assert baseline == make_baseline(time_range=time_range)
    assert hash(baseline) == hash(make_baseline(time_range=time_range))
    with pytest.raises((FrozenInstanceError, AttributeError)):
        baseline.mean = 1.0  # type: ignore[misc]


def test_personal_baseline_one_sample_properties() -> None:
    baseline = make_baseline(
        sample_count=1,
        mean=10.0,
        median=10.0,
        minimum=10,
        maximum=10,
        population_standard_deviation=0.0,
        last_observed_at=OBSERVED_AT,
    )

    assert baseline.has_multiple_samples is False
    assert baseline.observation_span == timedelta(0)


def test_personal_baseline_multiple_sample_properties_across_timezones() -> None:
    last = datetime.fromisoformat("2026-01-04T14:00:00+05:30")
    baseline = make_baseline(last_observed_at=last)

    assert baseline.has_multiple_samples is True
    assert baseline.observation_span == timedelta(days=2)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("profile_id", PROFILE_ID.value),
        ("profile_id", RECORD_ID),
        ("metric", MetricIdentifier.STEPS.value),
        ("metric", UnrelatedEnum.VALUE),
        ("unit", MeasurementUnit.COUNT.value),
        ("unit", UnrelatedEnum.VALUE),
        ("time_range", "all-time"),
    ],
)
def test_personal_baseline_rejects_invalid_typed_fields(field: str, value: object) -> None:
    with pytest.raises(AnalyticsValidationError, match=field):
        make_baseline(**{field: value})


def test_personal_baseline_rejects_noncanonical_unit() -> None:
    with pytest.raises(AnalyticsValidationError, match="unit must be 'count'"):
        make_baseline(unit=MeasurementUnit.HOURS)


@pytest.mark.parametrize("sample_count", [True, False, 0, -1, 1.0, "1"])
def test_personal_baseline_rejects_invalid_sample_count(sample_count: object) -> None:
    with pytest.raises(AnalyticsValidationError, match="sample_count"):
        make_baseline(sample_count=sample_count)


@pytest.mark.parametrize("field", ["mean", "median", "population_standard_deviation"])
@pytest.mark.parametrize("value", [0, True, nan, inf, -inf, "1"])
def test_personal_baseline_requires_finite_float_statistics(field: str, value: object) -> None:
    with pytest.raises(AnalyticsValidationError, match=field):
        make_baseline(**{field: value})


@pytest.mark.parametrize("field", ["minimum", "maximum"])
@pytest.mark.parametrize("value", [True, nan, inf, -inf, "1", None])
def test_personal_baseline_requires_finite_numeric_extrema(field: str, value: object) -> None:
    with pytest.raises(AnalyticsValidationError, match=field):
        make_baseline(**{field: value})


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"minimum": 21}, "minimum must not exceed"),
        ({"mean": 21.0}, "mean must be between"),
        ({"mean": 9.0}, "mean must be between"),
        ({"median": 21.0}, "median must be between"),
        ({"median": 9.0}, "median must be between"),
        ({"population_standard_deviation": -0.1}, "must be non-negative"),
        (
            {
                "sample_count": 1,
                "mean": 15.0,
                "median": 15.0,
                "minimum": 15,
                "maximum": 15,
                "population_standard_deviation": 1.0,
                "last_observed_at": OBSERVED_AT,
            },
            "must be 0.0 for one sample",
        ),
    ],
)
def test_personal_baseline_rejects_mathematical_inconsistency(
    overrides: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(AnalyticsValidationError, match=message):
        make_baseline(**overrides)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("first_observed_at", datetime(2026, 1, 2)),
        ("last_observed_at", date(2026, 1, 4)),
        ("first_observed_at", datetime(2026, 1, 2, tzinfo=MissingOffsetTimezone())),
        ("last_observed_at", datetime(2026, 1, 4, tzinfo=BrokenTimezone())),
    ],
)
def test_personal_baseline_rejects_invalid_observation_timestamps(
    field: str,
    value: object,
) -> None:
    with pytest.raises(AnalyticsValidationError, match=field):
        make_baseline(**{field: value})


def test_personal_baseline_rejects_reversed_observation_bounds() -> None:
    with pytest.raises(AnalyticsValidationError, match="must not follow"):
        make_baseline(first_observed_at=OBSERVED_AT + timedelta(days=3))


def test_personal_baseline_requires_matching_bounds_for_one_sample() -> None:
    with pytest.raises(AnalyticsValidationError, match="must match for one sample"):
        make_baseline(
            sample_count=1,
            mean=15.0,
            median=15.0,
            minimum=15,
            maximum=15,
            population_standard_deviation=0.0,
        )


def test_personal_baseline_exposes_no_interpretive_properties() -> None:
    baseline = make_baseline()

    for attribute in (
        "is_healthy",
        "is_normal",
        "is_improving",
        "risk",
        "recommendation",
        "prediction",
        "confidence",
    ):
        assert not hasattr(baseline, attribute)
