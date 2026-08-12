"""Behavior tests for deterministic basic wellness trend analytics."""

from datetime import UTC, date, datetime, timedelta, timezone
from math import inf, nan
from pathlib import Path

import pytest

import lifelenz.analytics
import lifelenz.application
import lifelenz.domain
import lifelenz.repositories
from lifelenz.analytics import (
    AnalyticsValidationError,
    InsufficientTrendDataError,
    MetricSample,
    MetricSampleExtractor,
    PersonalBaselineCalculator,
    TrendDirection,
    WellnessTrendCalculator,
)
from lifelenz.domain import (
    BodyMeasurementRecord,
    DailyActivityRecord,
    DailyNutritionRecord,
    DataSource,
    HydrationRecord,
    MealNutrition,
    MealRecord,
    MealType,
    MeasurementUnit,
    MenstrualBleedingRecord,
    MenstrualCycleRecord,
    MenstrualFlow,
    MetricIdentifier,
    ProfileId,
    RecordId,
    RecordMetadata,
    SleepRecord,
    SubjectiveScore,
    SubjectiveWellnessCheckIn,
    TimeRange,
    WorkoutRecord,
    WorkoutType,
)
from lifelenz.domain.taxonomy import DEFAULT_UNIT_BY_METRIC

PROFILE_ID = ProfileId("00000000-0000-4000-8000-000000000001")
OTHER_PROFILE_ID = ProfileId("00000000-0000-4000-8000-000000000002")
BASE_TIME = datetime(2026, 3, 1, 8, tzinfo=UTC)


def sample(
    value: int | float,
    *,
    day: float = 0.0,
    profile_id: ProfileId = PROFILE_ID,
    metric: MetricIdentifier = MetricIdentifier.STEPS,
    source_record_id: str = "sample-1",
    observed_at: datetime | None = None,
) -> MetricSample:
    timestamp = BASE_TIME + timedelta(days=day) if observed_at is None else observed_at
    return MetricSample(
        profile_id,
        metric,
        value,
        DEFAULT_UNIT_BY_METRIC[metric],
        timestamp,
        RecordId(source_record_id),
    )


def metadata(record_id: str, *, day: float = 0.0) -> RecordMetadata:
    return RecordMetadata(
        RecordId(record_id),
        BASE_TIME + timedelta(days=day),
        DataSource.MANUAL,
    )


def sleep_record(record_id: str, value: int | float, *, day: float) -> SleepRecord:
    return SleepRecord(
        metadata(record_id, day=day),
        TimeRange(BASE_TIME - timedelta(hours=10), BASE_TIME),
        sleep_minutes=value * 60,
        awake_minutes=0,
    )


def activity_record(record_id: str, value: int, *, day: float) -> DailyActivityRecord:
    return DailyActivityRecord(
        metadata(record_id, day=day),
        date(2026, 3, 1),
        steps=value,
        distance_kilometers=5,
        active_minutes=30,
        active_calories_kcal=200,
    )


def workout_record(record_id: str, minutes: int, *, day: float) -> WorkoutRecord:
    start = BASE_TIME + timedelta(days=day)
    return WorkoutRecord(
        metadata(record_id, day=day),
        TimeRange(start, start + timedelta(minutes=minutes)),
        WorkoutType.WALKING,
    )


def hydration_record(record_id: str, value: int | float, *, day: float) -> HydrationRecord:
    return HydrationRecord(metadata(record_id, day=day), value)


def nutrition_record(record_id: str, value: int | float, *, day: float) -> DailyNutritionRecord:
    return DailyNutritionRecord(
        metadata(record_id, day=day),
        date(2026, 3, 1),
        MealNutrition(calories_kcal=value),
    )


def body_record(record_id: str, value: int | float, *, day: float) -> BodyMeasurementRecord:
    return BodyMeasurementRecord(metadata(record_id, day=day), weight_kilograms=value)


def checkin(record_id: str, value: int, *, day: float) -> SubjectiveWellnessCheckIn:
    return SubjectiveWellnessCheckIn(
        metadata(record_id, day=day),
        SubjectiveScore(value),
        SubjectiveScore(5),
        SubjectiveScore(5),
    )


def meal_record(record_id: str) -> MealRecord:
    return MealRecord(
        metadata(record_id),
        MealType.LUNCH,
        MealNutrition(calories_kcal=500),
    )


class SleepRecordSubclass(SleepRecord):
    pass


class MetricSampleSubclass(MetricSample):
    pass


@pytest.mark.parametrize(
    (
        "values",
        "expected_change",
        "expected_percentage",
        "expected_slope",
        "expected_direction",
    ),
    [
        ((10, 15), 5.0, 50.0, 5.0, TrendDirection.INCREASING),
        ((10, 5), -5.0, -50.0, -5.0, TrendDirection.DECREASING),
        ((10, 10), 0.0, 0.0, 0.0, TrendDirection.STABLE),
        ((-10, -5), 5.0, 50.0, 5.0, TrendDirection.INCREASING),
        ((-10, -15), -5.0, -50.0, -5.0, TrendDirection.DECREASING),
        ((-5, 5), 10.0, 200.0, 10.0, TrendDirection.INCREASING),
        ((0, 5), 5.0, None, 5.0, TrendDirection.INCREASING),
        ((1.5, 2.25), 0.75, 50.0, 0.75, TrendDirection.INCREASING),
    ],
)
def test_two_sample_endpoint_change_percentage_slope_and_direction(
    values: tuple[int | float, int | float],
    expected_change: float,
    expected_percentage: float | None,
    expected_slope: float,
    expected_direction: TrendDirection,
) -> None:
    samples = (
        sample(values[0], source_record_id="first"),
        sample(values[1], day=1, source_record_id="last"),
    )

    trend = WellnessTrendCalculator().calculate(
        PROFILE_ID,
        MetricIdentifier.STEPS,
        samples,
    )

    assert trend.sample_count == 2
    assert trend.first_value == values[0]
    assert trend.last_value == values[1]
    assert trend.absolute_change == expected_change
    assert trend.percentage_change == expected_percentage
    assert trend.slope_per_day == expected_slope
    assert trend.direction is expected_direction
    assert trend.unit is MeasurementUnit.COUNT
    assert trend.stability_tolerance == 0.0
    assert trend.time_range is None


@pytest.mark.parametrize(
    ("ending_value", "tolerance", "expected_direction"),
    [
        (10.5, 1.0, TrendDirection.STABLE),
        (9.5, 1.0, TrendDirection.STABLE),
        (11.0, 1.0, TrendDirection.STABLE),
        (9.0, 1.0, TrendDirection.STABLE),
        (11.000001, 1.0, TrendDirection.INCREASING),
        (8.999999, 1.0, TrendDirection.DECREASING),
    ],
)
def test_tolerance_boundaries_are_inclusive_for_stability(
    ending_value: float,
    tolerance: float,
    expected_direction: TrendDirection,
) -> None:
    trend = WellnessTrendCalculator().calculate(
        PROFILE_ID,
        MetricIdentifier.STEPS,
        (sample(10, source_record_id="a"), sample(ending_value, day=1, source_record_id="b")),
        stability_tolerance=tolerance,
    )

    assert trend.direction is expected_direction
    assert trend.stability_tolerance == tolerance


@pytest.mark.parametrize(
    ("points", "expected_slope"),
    [
        (((0.0, 1), (1.0, 3), (2.0, 5)), 2.0),
        (((0.0, 1), (1.0, 2), (3.0, 5)), 19 / 14),
        (((0.0, 0), (1.0, 3), (2.0, 2)), 1.0),
        (((0.0, 3), (1.0, 0), (2.0, 1)), -1.0),
        (((0.0, 4), (1.0, 4), (2.0, 4), (3.0, 4)), 0.0),
        (((0.0, 0), (0.5, 12)), 24.0),
        (((0.0, 0), (2.0, 10)), 5.0),
    ],
)
def test_least_squares_slope_for_deterministic_time_series(
    points: tuple[tuple[float, int | float], ...],
    expected_slope: float,
) -> None:
    samples = tuple(
        sample(value, day=day, source_record_id=f"sample-{index}")
        for index, (day, value) in enumerate(points)
    )

    trend = WellnessTrendCalculator().calculate(
        PROFILE_ID,
        MetricIdentifier.STEPS,
        samples,
    )

    assert trend.slope_per_day == pytest.approx(expected_slope)


def test_same_timestamp_samples_have_zero_slope_and_record_id_endpoints() -> None:
    samples = (
        sample(20, source_record_id="z"),
        sample(10, source_record_id="a"),
        sample(15, source_record_id="m"),
    )

    trend = WellnessTrendCalculator().calculate(
        PROFILE_ID,
        MetricIdentifier.STEPS,
        samples,
    )

    assert trend.first_value == 10
    assert trend.last_value == 20
    assert trend.absolute_change == 10.0
    assert trend.slope_per_day == 0.0
    assert trend.direction is TrendDirection.STABLE
    assert trend.first_observed_at == trend.last_observed_at == BASE_TIME


def test_filtering_uses_exact_profile_metric_and_start_inclusive_end_exclusive_range() -> None:
    requested_range = TimeRange(BASE_TIME, BASE_TIME + timedelta(days=2))
    samples = (
        sample(1, day=-1, source_record_id="before"),
        sample(2, day=0, source_record_id="start"),
        sample(6, day=1, source_record_id="inside"),
        sample(10, day=2, source_record_id="end"),
        sample(20, day=1, profile_id=OTHER_PROFILE_ID, source_record_id="other-profile"),
        sample(
            30,
            day=1,
            metric=MetricIdentifier.CALORIES,
            source_record_id="other-metric",
        ),
    )

    trend = WellnessTrendCalculator().calculate(
        PROFILE_ID,
        MetricIdentifier.STEPS,
        samples,
        time_range=requested_range,
    )

    assert trend.sample_count == 2
    assert trend.first_value == 2
    assert trend.last_value == 6
    assert trend.first_observed_at == BASE_TIME
    assert trend.last_observed_at == BASE_TIME + timedelta(days=1)
    assert trend.time_range is requested_range


def test_no_time_range_includes_all_matching_samples() -> None:
    trend = WellnessTrendCalculator().calculate(
        PROFILE_ID,
        MetricIdentifier.STEPS,
        (
            sample(1, day=-100, source_record_id="early"),
            sample(3, day=100, source_record_id="late"),
        ),
    )

    assert trend.sample_count == 2
    assert trend.observation_span == timedelta(days=200)


@pytest.mark.parametrize(
    "samples, time_range",
    [
        ((), None),
        ((sample(1),), None),
        (
            (
                sample(1, profile_id=OTHER_PROFILE_ID, source_record_id="a"),
                sample(2, profile_id=OTHER_PROFILE_ID, source_record_id="b"),
            ),
            None,
        ),
        (
            (
                sample(1, metric=MetricIdentifier.CALORIES, source_record_id="a"),
                sample(2, metric=MetricIdentifier.CALORIES, source_record_id="b"),
            ),
            None,
        ),
        (
            (sample(1, day=0, source_record_id="a"), sample(2, day=2, source_record_id="b")),
            TimeRange(BASE_TIME, BASE_TIME + timedelta(days=1)),
        ),
        (
            (sample(1, day=-2, source_record_id="a"), sample(2, day=-1, source_record_id="b")),
            TimeRange(BASE_TIME, BASE_TIME + timedelta(days=1)),
        ),
    ],
)
def test_valid_but_insufficient_samples_raise_contextual_error(
    samples: tuple[MetricSample, ...],
    time_range: TimeRange | None,
) -> None:
    with pytest.raises(InsufficientTrendDataError) as caught:
        WellnessTrendCalculator().calculate(
            PROFILE_ID,
            MetricIdentifier.STEPS,
            samples,
            time_range=time_range,
        )

    assert PROFILE_ID.value in str(caught.value)
    assert MetricIdentifier.STEPS.value in str(caught.value)
    assert "at least two" in str(caught.value)


def test_shuffled_inputs_produce_equal_results_without_mutating_tuple() -> None:
    samples = (
        sample(9, day=2, source_record_id="last"),
        sample(1, day=0, source_record_id="first"),
        sample(4, day=1, source_record_id="middle"),
    )
    original = tuple(samples)
    calculator = WellnessTrendCalculator()

    first = calculator.calculate(PROFILE_ID, MetricIdentifier.STEPS, samples)
    second = calculator.calculate(
        PROFILE_ID,
        MetricIdentifier.STEPS,
        tuple(reversed(samples)),
    )

    assert first == second
    assert first.first_value == 1
    assert first.last_value == 9
    assert samples == original


def test_equivalent_timestamp_offsets_use_record_id_tie_break() -> None:
    utc_time = BASE_TIME
    offset_time = datetime(2026, 3, 1, 13, 30, tzinfo=timezone(timedelta(hours=5, minutes=30)))

    trend = WellnessTrendCalculator().calculate(
        PROFILE_ID,
        MetricIdentifier.STEPS,
        (
            sample(8, observed_at=offset_time, source_record_id="z"),
            sample(2, observed_at=utc_time, source_record_id="a"),
        ),
    )

    assert trend.first_value == 2
    assert trend.last_value == 8
    assert trend.slope_per_day == 0.0


@pytest.mark.parametrize("profile_id", [None, PROFILE_ID.value, RecordId("wrong")])
def test_calculate_validates_profile_before_other_arguments(profile_id: object) -> None:
    with pytest.raises(AnalyticsValidationError, match="profile_id"):
        WellnessTrendCalculator().calculate(profile_id, "steps", [])  # type: ignore[arg-type]


@pytest.mark.parametrize("metric", [None, "steps", MeasurementUnit.COUNT])
def test_calculate_rejects_invalid_metric(metric: object) -> None:
    with pytest.raises(AnalyticsValidationError, match="metric"):
        WellnessTrendCalculator().calculate(PROFILE_ID, metric, ())  # type: ignore[arg-type]


@pytest.mark.parametrize("samples", [[], {}, None, "samples", iter(())])
def test_calculate_requires_exact_tuple(samples: object) -> None:
    with pytest.raises(AnalyticsValidationError, match="samples"):
        WellnessTrendCalculator().calculate(
            PROFILE_ID,
            MetricIdentifier.STEPS,
            samples,  # type: ignore[arg-type]
        )


def test_calculate_validates_time_range_before_tolerance_and_elements() -> None:
    with pytest.raises(AnalyticsValidationError, match="time_range"):
        WellnessTrendCalculator().calculate(
            PROFILE_ID,
            MetricIdentifier.STEPS,
            (object(),),  # type: ignore[arg-type]
            time_range="today",  # type: ignore[arg-type]
            stability_tolerance=True,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("tolerance", [True, 0, -0.1, nan, inf, -inf, "0", None])
def test_calculate_rejects_invalid_stability_tolerance(tolerance: object) -> None:
    with pytest.raises(AnalyticsValidationError, match="stability_tolerance"):
        WellnessTrendCalculator().calculate(
            PROFILE_ID,
            MetricIdentifier.STEPS,
            (object(),),  # type: ignore[arg-type]
            stability_tolerance=tolerance,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("bad_sample", [None, {}, object()])
def test_calculate_rejects_invalid_sample_elements(bad_sample: object) -> None:
    with pytest.raises(AnalyticsValidationError, match="every sample"):
        WellnessTrendCalculator().calculate(
            PROFILE_ID,
            MetricIdentifier.STEPS,
            (bad_sample,),  # type: ignore[arg-type]
        )


def test_calculate_rejects_metric_sample_subclass() -> None:
    derived = MetricSampleSubclass(
        PROFILE_ID,
        MetricIdentifier.STEPS,
        1,
        MeasurementUnit.COUNT,
        BASE_TIME,
        RecordId("derived"),
    )

    with pytest.raises(AnalyticsValidationError, match="exact MetricSample"):
        WellnessTrendCalculator().calculate(
            PROFILE_ID,
            MetricIdentifier.STEPS,
            (derived, derived),
        )


def test_calculator_defensively_rejects_noncanonical_retained_unit() -> None:
    malformed = sample(1, source_record_id="a")
    object.__setattr__(malformed, "unit", MeasurementUnit.HOURS)

    with pytest.raises(AnalyticsValidationError, match="canonical unit"):
        WellnessTrendCalculator().calculate(
            PROFILE_ID,
            MetricIdentifier.STEPS,
            (malformed, sample(2, day=1, source_record_id="b")),
        )


def test_calculator_rejects_endpoint_values_without_finite_float_arithmetic() -> None:
    with pytest.raises(AnalyticsValidationError, match="finite floating-point"):
        WellnessTrendCalculator().calculate(
            PROFILE_ID,
            MetricIdentifier.STEPS,
            (
                sample(-(10**1000), source_record_id="a"),
                sample(10**1000, day=1, source_record_id="b"),
            ),
        )


def test_calculator_rejects_intermediate_value_without_finite_float_arithmetic() -> None:
    with pytest.raises(AnalyticsValidationError, match="slope calculation"):
        WellnessTrendCalculator().calculate(
            PROFILE_ID,
            MetricIdentifier.STEPS,
            (
                sample(1, source_record_id="a"),
                sample(10**1000, day=1, source_record_id="b"),
                sample(2, day=2, source_record_id="c"),
            ),
        )


@pytest.mark.parametrize(
    ("records", "metric", "expected_values", "expected_unit"),
    [
        (
            (sleep_record("s1", 6, day=0), sleep_record("s2", 8, day=1)),
            MetricIdentifier.SLEEP_DURATION,
            (6.0, 8.0),
            MeasurementUnit.HOURS,
        ),
        (
            (activity_record("a1", 1000, day=0), activity_record("a2", 2000, day=1)),
            MetricIdentifier.STEPS,
            (1000, 2000),
            MeasurementUnit.COUNT,
        ),
        (
            (hydration_record("h1", 500, day=0), hydration_record("h2", 250, day=1)),
            MetricIdentifier.WATER_INTAKE,
            (500, 250),
            MeasurementUnit.MILLILITERS,
        ),
        (
            (nutrition_record("n1", 0, day=0), nutrition_record("n2", 2000, day=1)),
            MetricIdentifier.CALORIES,
            (0, 2000),
            MeasurementUnit.KCAL,
        ),
        (
            (body_record("b1", 70, day=0), body_record("b2", 72, day=1)),
            MetricIdentifier.WEIGHT,
            (70, 72),
            MeasurementUnit.KILOGRAMS,
        ),
        (
            (checkin("c1", 4, day=0), checkin("c2", 7, day=1)),
            MetricIdentifier.MOOD_SCORE,
            (4, 7),
            MeasurementUnit.SCORE,
        ),
        (
            (workout_record("w1", 30, day=0), workout_record("w2", 60, day=1)),
            MetricIdentifier.ACTIVE_MINUTES,
            (30.0, 60.0),
            MeasurementUnit.MINUTES,
        ),
    ],
)
def test_calculate_from_records_reuses_supported_canonical_extraction(
    records: tuple[object, ...],
    metric: MetricIdentifier,
    expected_values: tuple[int | float, int | float],
    expected_unit: MeasurementUnit,
) -> None:
    trend = WellnessTrendCalculator().calculate_from_records(
        PROFILE_ID,
        metric,
        records,  # type: ignore[arg-type]
    )

    assert (trend.first_value, trend.last_value) == expected_values
    assert trend.unit is expected_unit
    assert trend.profile_id is PROFILE_ID


def test_calculate_from_records_handles_mixed_records_and_time_filtering() -> None:
    requested_range = TimeRange(BASE_TIME, BASE_TIME + timedelta(days=2))
    records = (
        hydration_record("start", 200, day=0),
        activity_record("other-type", 5000, day=1),
        hydration_record("inside", 600, day=1),
        hydration_record("end", 1000, day=2),
    )

    trend = WellnessTrendCalculator().calculate_from_records(
        PROFILE_ID,
        MetricIdentifier.WATER_INTAKE,
        records,
        time_range=requested_range,
        stability_tolerance=100.0,
    )

    assert trend.sample_count == 2
    assert trend.first_value == 200
    assert trend.last_value == 600
    assert trend.direction is TrendDirection.INCREASING
    assert trend.time_range is requested_range


@pytest.mark.parametrize(
    "records, metric",
    [
        ((), MetricIdentifier.STEPS),
        ((meal_record("meal-1"), meal_record("meal-2")), MetricIdentifier.CALORIES),
        (
            (
                MenstrualBleedingRecord(metadata("bleeding"), MenstrualFlow.LIGHT),
                MenstrualCycleRecord(metadata("cycle"), date(2026, 3, 1), date(2026, 3, 4)),
            ),
            MetricIdentifier.STEPS,
        ),
        ((activity_record("only", 1000, day=0),), MetricIdentifier.STEPS),
    ],
)
def test_calculate_from_records_requires_two_extractable_selected_samples(
    records: tuple[object, ...],
    metric: MetricIdentifier,
) -> None:
    with pytest.raises(InsufficientTrendDataError):
        WellnessTrendCalculator().calculate_from_records(
            PROFILE_ID,
            metric,
            records,  # type: ignore[arg-type]
        )


def test_calculate_from_records_delegates_to_metric_sample_extractor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[ProfileId, object]] = []
    original_extract = MetricSampleExtractor.extract

    def tracking_extract(
        extractor: MetricSampleExtractor,
        profile_id: ProfileId,
        record: object,
    ) -> tuple[MetricSample, ...]:
        calls.append((profile_id, record))
        return original_extract(extractor, profile_id, record)  # type: ignore[arg-type]

    monkeypatch.setattr(MetricSampleExtractor, "extract", tracking_extract)
    records = (hydration_record("a", 100, day=0), hydration_record("b", 200, day=1))

    WellnessTrendCalculator().calculate_from_records(
        PROFILE_ID,
        MetricIdentifier.WATER_INTAKE,
        records,
    )

    assert calls == [(PROFILE_ID, records[0]), (PROFILE_ID, records[1])]


@pytest.mark.parametrize("profile_id", [None, PROFILE_ID.value, RecordId("wrong")])
def test_calculate_from_records_validates_profile_first(profile_id: object) -> None:
    with pytest.raises(AnalyticsValidationError, match="profile_id"):
        WellnessTrendCalculator().calculate_from_records(
            profile_id,  # type: ignore[arg-type]
            "steps",  # type: ignore[arg-type]
            [],  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("metric", [None, "steps", MeasurementUnit.COUNT])
def test_calculate_from_records_rejects_invalid_metric(metric: object) -> None:
    with pytest.raises(AnalyticsValidationError, match="metric"):
        WellnessTrendCalculator().calculate_from_records(
            PROFILE_ID,
            metric,  # type: ignore[arg-type]
            (),
        )


@pytest.mark.parametrize("records", [[], {}, None, "records", iter(())])
def test_calculate_from_records_requires_exact_tuple(records: object) -> None:
    with pytest.raises(AnalyticsValidationError, match="records"):
        WellnessTrendCalculator().calculate_from_records(
            PROFILE_ID,
            MetricIdentifier.STEPS,
            records,  # type: ignore[arg-type]
        )


def test_calculate_from_records_validates_range_before_tolerance_and_elements() -> None:
    with pytest.raises(AnalyticsValidationError, match="time_range"):
        WellnessTrendCalculator().calculate_from_records(
            PROFILE_ID,
            MetricIdentifier.STEPS,
            (object(),),  # type: ignore[arg-type]
            time_range="today",  # type: ignore[arg-type]
            stability_tolerance=True,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("tolerance", [True, 0, -0.1, nan, inf, -inf, "0", None])
def test_calculate_from_records_rejects_invalid_tolerance(tolerance: object) -> None:
    with pytest.raises(AnalyticsValidationError, match="stability_tolerance"):
        WellnessTrendCalculator().calculate_from_records(
            PROFILE_ID,
            MetricIdentifier.STEPS,
            (object(),),  # type: ignore[arg-type]
            stability_tolerance=tolerance,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("record", [None, {}, object()])
def test_calculate_from_records_rejects_unsupported_record(record: object) -> None:
    with pytest.raises(AnalyticsValidationError, match="record"):
        WellnessTrendCalculator().calculate_from_records(
            PROFILE_ID,
            MetricIdentifier.STEPS,
            (record,),  # type: ignore[arg-type]
        )


def test_calculate_from_records_rejects_record_subclass() -> None:
    base = sleep_record("base", 7, day=0)
    derived = SleepRecordSubclass(
        base.metadata,
        base.period,
        base.sleep_minutes,
        base.awake_minutes,
    )

    with pytest.raises(AnalyticsValidationError, match="exact supported"):
        WellnessTrendCalculator().calculate_from_records(
            PROFILE_ID,
            MetricIdentifier.SLEEP_DURATION,
            (derived,),
        )


def test_baseline_and_trend_remain_distinct_with_different_minimum_counts() -> None:
    one_sample = (sample(4),)

    baseline = PersonalBaselineCalculator().calculate(
        PROFILE_ID,
        MetricIdentifier.STEPS,
        one_sample,
    )
    assert baseline.sample_count == 1
    with pytest.raises(InsufficientTrendDataError):
        WellnessTrendCalculator().calculate(
            PROFILE_ID,
            MetricIdentifier.STEPS,
            one_sample,
        )


def test_public_api_and_dependency_boundaries_include_only_intended_trend_symbols() -> None:
    expected = [
        "AnalyticsError",
        "AnalyticsValidationError",
        "InsufficientBaselineDataError",
        "InsufficientTrendDataError",
        "MetricSample",
        "MetricSampleExtractor",
        "PersonalBaseline",
        "PersonalBaselineCalculator",
        "TrendDirection",
        "WellnessTrend",
        "WellnessTrendCalculator",
    ]

    assert lifelenz.analytics.__all__ == expected
    assert lifelenz.analytics.__all__ == sorted(lifelenz.analytics.__all__)
    assert len(lifelenz.analytics.__all__) == len(set(lifelenz.analytics.__all__))
    assert all(hasattr(lifelenz.analytics, name) for name in expected)
    assert not any(name.startswith("_") for name in lifelenz.analytics.__all__)
    assert not set(expected) & set(lifelenz.domain.__all__)
    assert not set(expected) & set(lifelenz.repositories.__all__)
    assert not set(expected) & set(lifelenz.application.__all__)
    assert len(lifelenz.domain.__all__) == 48
    assert len(lifelenz.repositories.__all__) == 19
    assert len(lifelenz.application.__all__) == 23

    root = Path(__file__).parents[3]
    production = root / "src" / "lifelenz"
    trend_source = (production / "analytics" / "trends.py").read_text(encoding="utf-8")
    assert "lifelenz.repositories" not in trend_source
    assert "lifelenz.application" not in trend_source
    assert "PersonalBaselineCalculator" not in trend_source
