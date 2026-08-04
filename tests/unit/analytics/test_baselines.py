"""Behavior tests for canonical extraction and personal baseline calculation."""

from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path
from statistics import pstdev

import pytest

import lifelenz.analytics
import lifelenz.application
import lifelenz.domain
import lifelenz.repositories
from lifelenz.analytics import (
    AnalyticsValidationError,
    InsufficientBaselineDataError,
    MetricSample,
    MetricSampleExtractor,
    PersonalBaselineCalculator,
)
from lifelenz.domain import (
    BeverageType,
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
BASE_TIME = datetime(2026, 2, 1, 8, tzinfo=UTC)


def metadata(record_id: str, *, hour: int = 0) -> RecordMetadata:
    return RecordMetadata(
        RecordId(record_id),
        BASE_TIME + timedelta(hours=hour),
        DataSource.MANUAL,
    )


def sleep_record(record_id: str = "sleep-1", *, hour: int = 0, minutes: int = 420) -> SleepRecord:
    return SleepRecord(
        metadata(record_id, hour=hour),
        TimeRange(BASE_TIME - timedelta(hours=8), BASE_TIME),
        sleep_minutes=minutes,
        awake_minutes=0,
    )


def activity_record(record_id: str = "activity-1", *, hour: int = 0) -> DailyActivityRecord:
    return DailyActivityRecord(
        metadata(record_id, hour=hour),
        date(2026, 2, 1),
        steps=8000,
        distance_kilometers=5.5,
        active_minutes=45,
        active_calories_kcal=320.5,
    )


def workout_record(record_id: str = "workout-1", *, hour: int = 0) -> WorkoutRecord:
    start = BASE_TIME + timedelta(hours=hour)
    return WorkoutRecord(
        metadata(record_id, hour=hour),
        TimeRange(start, start + timedelta(minutes=75)),
        WorkoutType.WALKING,
        distance_kilometers=4,
        active_calories_kcal=250,
    )


def hydration_record(
    record_id: str = "hydration-1",
    *,
    hour: int = 0,
    volume: int | float = 350,
) -> HydrationRecord:
    return HydrationRecord(metadata(record_id, hour=hour), volume, BeverageType.WATER)


def daily_nutrition_record(
    record_id: str = "nutrition-1",
    *,
    hour: int = 0,
    nutrition: MealNutrition | None = None,
) -> DailyNutritionRecord:
    return DailyNutritionRecord(
        metadata(record_id, hour=hour),
        date(2026, 2, 1),
        nutrition
        or MealNutrition(
            calories_kcal=2100,
            protein_grams=90,
            carbohydrates_grams=250,
            fat_grams=70,
            fibre_grams=28,
        ),
        meal_count=3,
    )


def meal_record(record_id: str = "meal-1", *, hour: int = 0) -> MealRecord:
    return MealRecord(
        metadata(record_id, hour=hour),
        MealType.LUNCH,
        MealNutrition(calories_kcal=600, protein_grams=25),
    )


def body_record(
    record_id: str = "body-1",
    *,
    hour: int = 0,
    height: int | float | None = 1.75,
    body_fat: int | float | None = 20,
) -> BodyMeasurementRecord:
    return BodyMeasurementRecord(
        metadata(record_id, hour=hour),
        weight_kilograms=72.5,
        height_meters=height,
        body_fat_percent=body_fat,
    )


def checkin(record_id: str = "checkin-1", *, hour: int = 0) -> SubjectiveWellnessCheckIn:
    return SubjectiveWellnessCheckIn(
        metadata(record_id, hour=hour),
        mood_score=SubjectiveScore(7),
        energy_score=SubjectiveScore(6),
        stress_score=SubjectiveScore(4),
        motivation_score=SubjectiveScore(8),
    )


def bleeding_record(record_id: str = "bleeding-1") -> MenstrualBleedingRecord:
    return MenstrualBleedingRecord(metadata(record_id), MenstrualFlow.LIGHT)


def cycle_record(record_id: str = "cycle-1") -> MenstrualCycleRecord:
    return MenstrualCycleRecord(metadata(record_id), date(2026, 2, 1), date(2026, 2, 5))


def sample(
    value: int | float,
    *,
    profile_id: ProfileId = PROFILE_ID,
    metric: MetricIdentifier = MetricIdentifier.STEPS,
    observed_at: datetime = BASE_TIME,
    source_record_id: str = "sample-1",
) -> MetricSample:
    return MetricSample(
        profile_id,
        metric,
        value,
        DEFAULT_UNIT_BY_METRIC[metric],
        observed_at,
        RecordId(source_record_id),
    )


class SleepRecordSubclass(SleepRecord):
    pass


class MetricSampleSubclass(MetricSample):
    pass


@pytest.mark.parametrize(
    ("record", "expected"),
    [
        (
            sleep_record(),
            [(MetricIdentifier.SLEEP_DURATION, 7.0, MeasurementUnit.HOURS)],
        ),
        (
            activity_record(),
            [
                (MetricIdentifier.ACTIVE_CALORIES, 320.5, MeasurementUnit.KCAL),
                (MetricIdentifier.ACTIVE_MINUTES, 45, MeasurementUnit.MINUTES),
                (MetricIdentifier.DISTANCE, 5.5, MeasurementUnit.KILOMETERS),
                (MetricIdentifier.STEPS, 8000, MeasurementUnit.COUNT),
            ],
        ),
        (
            workout_record(),
            [(MetricIdentifier.ACTIVE_MINUTES, 75.0, MeasurementUnit.MINUTES)],
        ),
        (
            hydration_record(),
            [(MetricIdentifier.WATER_INTAKE, 350, MeasurementUnit.MILLILITERS)],
        ),
        (
            daily_nutrition_record(),
            [
                (MetricIdentifier.CALORIES, 2100, MeasurementUnit.KCAL),
                (MetricIdentifier.CARBOHYDRATES, 250, MeasurementUnit.GRAMS),
                (MetricIdentifier.FAT, 70, MeasurementUnit.GRAMS),
                (MetricIdentifier.FIBRE, 28, MeasurementUnit.GRAMS),
                (MetricIdentifier.PROTEIN, 90, MeasurementUnit.GRAMS),
            ],
        ),
        (meal_record(), []),
        (
            body_record(),
            [
                (MetricIdentifier.BODY_FAT, 20, MeasurementUnit.PERCENT),
                (MetricIdentifier.HEIGHT, 1.75, MeasurementUnit.METERS),
                (MetricIdentifier.WEIGHT, 72.5, MeasurementUnit.KILOGRAMS),
            ],
        ),
        (
            checkin(),
            [
                (MetricIdentifier.ENERGY_SCORE, 6, MeasurementUnit.SCORE),
                (MetricIdentifier.MOOD_SCORE, 7, MeasurementUnit.SCORE),
                (MetricIdentifier.STRESS_SCORE, 4, MeasurementUnit.SCORE),
            ],
        ),
        (bleeding_record(), []),
        (cycle_record(), []),
    ],
)
def test_extractor_maps_every_record_type_to_canonical_samples(
    record: object,
    expected: list[tuple[MetricIdentifier, int | float, MeasurementUnit]],
) -> None:
    samples = MetricSampleExtractor().extract(PROFILE_ID, record)  # type: ignore[arg-type]

    assert [(item.metric, item.value, item.unit) for item in samples] == expected
    assert type(samples) is tuple
    assert all(item.profile_id is PROFILE_ID for item in samples)
    assert all(item.observed_at is record.metadata.recorded_at for item in samples)  # type: ignore[attr-defined]
    assert all(item.source_record_id is record.metadata.record_id for item in samples)  # type: ignore[attr-defined]


def test_sleep_extraction_emits_only_one_hours_sample_without_quality_or_stage_metrics() -> None:
    samples = MetricSampleExtractor().extract(PROFILE_ID, sleep_record(minutes=450))

    assert samples[0].value == 7.5
    assert samples[0].unit is MeasurementUnit.HOURS
    assert len(samples) == 1


def test_daily_nutrition_skips_unknown_optional_metrics() -> None:
    record = daily_nutrition_record(nutrition=MealNutrition(calories_kcal=1800))

    samples = MetricSampleExtractor().extract(PROFILE_ID, record)

    assert [(item.metric, item.value) for item in samples] == [(MetricIdentifier.CALORIES, 1800)]


def test_body_extraction_skips_absent_fields_and_does_not_calculate_bmi() -> None:
    samples = MetricSampleExtractor().extract(PROFILE_ID, body_record(height=None, body_fat=None))

    assert [(item.metric, item.value) for item in samples] == [(MetricIdentifier.WEIGHT, 72.5)]
    assert all(item.metric is not MetricIdentifier.BMI for item in samples)


def test_subjective_extraction_ignores_motivation_and_categorical_context() -> None:
    samples = MetricSampleExtractor().extract(PROFILE_ID, checkin())

    assert {item.metric for item in samples} == {
        MetricIdentifier.MOOD_SCORE,
        MetricIdentifier.ENERGY_SCORE,
        MetricIdentifier.STRESS_SCORE,
    }


def test_meal_calories_are_not_duplicated_with_daily_nutrition() -> None:
    extractor = MetricSampleExtractor()

    assert extractor.extract(PROFILE_ID, meal_record()) == ()
    assert [item.metric for item in extractor.extract(PROFILE_ID, daily_nutrition_record())].count(
        MetricIdentifier.CALORIES
    ) == 1


def test_extraction_is_repeatable_and_does_not_mutate_record() -> None:
    record = activity_record()
    original = repr(record)
    extractor = MetricSampleExtractor()

    first = extractor.extract(PROFILE_ID, record)
    second = extractor.extract(PROFILE_ID, record)

    assert first == second
    assert repr(record) == original


@pytest.mark.parametrize("profile_id", [None, PROFILE_ID.value, RecordId("wrong-kind"), {}])
def test_extractor_rejects_invalid_profile(profile_id: object) -> None:
    with pytest.raises(AnalyticsValidationError, match="profile_id"):
        MetricSampleExtractor().extract(profile_id, sleep_record())  # type: ignore[arg-type]


@pytest.mark.parametrize("record", [None, {}, "sleep", 1, object()])
def test_extractor_rejects_unsupported_objects(record: object) -> None:
    with pytest.raises(AnalyticsValidationError, match="record"):
        MetricSampleExtractor().extract(PROFILE_ID, record)  # type: ignore[arg-type]


def test_extractor_rejects_supported_record_subclass() -> None:
    base = sleep_record()
    derived = SleepRecordSubclass(
        base.metadata,
        base.period,
        base.sleep_minutes,
        base.awake_minutes,
    )

    with pytest.raises(AnalyticsValidationError, match="exact supported"):
        MetricSampleExtractor().extract(PROFILE_ID, derived)


def test_calculator_one_sample_contract() -> None:
    observation = sample(12)

    baseline = PersonalBaselineCalculator().calculate(
        PROFILE_ID,
        MetricIdentifier.STEPS,
        (observation,),
    )

    assert baseline.sample_count == 1
    assert baseline.mean == 12.0
    assert baseline.median == 12.0
    assert baseline.minimum == 12
    assert baseline.maximum == 12
    assert baseline.population_standard_deviation == 0.0
    assert baseline.first_observed_at is observation.observed_at
    assert baseline.last_observed_at is observation.observed_at
    assert baseline.time_range is None
    assert baseline.has_multiple_samples is False
    assert baseline.observation_span == timedelta(0)


@pytest.mark.parametrize(
    ("values", "expected_median"),
    [
        ((1, 5, 9), 5.0),
        ((1, 5, 9, 11), 7.0),
        ((1.25, 2.5, 10.75), 2.5),
        ((-5, 0.5, 5), 0.5),
        ((3, 3, 3), 3.0),
    ],
)
def test_calculator_multiple_sample_statistics_without_rounding(
    values: tuple[int | float, ...],
    expected_median: float,
) -> None:
    samples = tuple(
        sample(
            value,
            observed_at=BASE_TIME + timedelta(hours=index),
            source_record_id=f"sample-{index}",
        )
        for index, value in enumerate(values)
    )

    baseline = PersonalBaselineCalculator().calculate(
        PROFILE_ID,
        MetricIdentifier.STEPS,
        samples,
    )

    assert baseline.sample_count == len(values)
    assert baseline.mean == pytest.approx(sum(values) / len(values))
    assert type(baseline.mean) is float
    assert baseline.median == expected_median
    assert type(baseline.median) is float
    assert baseline.minimum == min(values)
    assert type(baseline.minimum) is type(min(values))
    assert baseline.maximum == max(values)
    assert baseline.population_standard_deviation == pytest.approx(pstdev(values))
    assert type(baseline.population_standard_deviation) is float


def test_calculator_filters_profile_metric_and_start_inclusive_end_exclusive_range() -> None:
    start = BASE_TIME
    end = BASE_TIME + timedelta(days=2)
    requested_range = TimeRange(start, end)
    samples = (
        sample(1, observed_at=start - timedelta(microseconds=1), source_record_id="before"),
        sample(2, observed_at=start, source_record_id="start"),
        sample(4, observed_at=end - timedelta(microseconds=1), source_record_id="inside"),
        sample(8, observed_at=end, source_record_id="end"),
        sample(
            16, profile_id=OTHER_PROFILE_ID, observed_at=start, source_record_id="other-profile"
        ),
        sample(
            32,
            metric=MetricIdentifier.CALORIES,
            observed_at=start,
            source_record_id="other-metric",
        ),
    )

    baseline = PersonalBaselineCalculator().calculate(
        PROFILE_ID,
        MetricIdentifier.STEPS,
        samples,
        time_range=requested_range,
    )

    assert baseline.sample_count == 2
    assert baseline.mean == 3.0
    assert baseline.minimum == 2
    assert baseline.maximum == 4
    assert baseline.first_observed_at == start
    assert baseline.last_observed_at == end - timedelta(microseconds=1)
    assert baseline.time_range is requested_range


def test_no_time_range_includes_all_matching_samples() -> None:
    samples = (
        sample(1, observed_at=BASE_TIME - timedelta(days=100), source_record_id="early"),
        sample(3, observed_at=BASE_TIME + timedelta(days=100), source_record_id="late"),
    )

    baseline = PersonalBaselineCalculator().calculate(
        PROFILE_ID,
        MetricIdentifier.STEPS,
        samples,
    )

    assert baseline.sample_count == 2
    assert baseline.mean == 2.0


@pytest.mark.parametrize(
    "samples, time_range",
    [
        ((), None),
        ((sample(1, profile_id=OTHER_PROFILE_ID),), None),
        ((sample(1, metric=MetricIdentifier.CALORIES),), None),
        (
            (sample(1, observed_at=BASE_TIME - timedelta(days=1)),),
            TimeRange(BASE_TIME, BASE_TIME + timedelta(days=1)),
        ),
    ],
)
def test_calculator_reports_context_when_no_matching_data_remains(
    samples: tuple[MetricSample, ...],
    time_range: TimeRange | None,
) -> None:
    with pytest.raises(InsufficientBaselineDataError) as caught:
        PersonalBaselineCalculator().calculate(
            PROFILE_ID,
            MetricIdentifier.STEPS,
            samples,
            time_range=time_range,
        )

    assert PROFILE_ID.value in str(caught.value)
    assert MetricIdentifier.STEPS.value in str(caught.value)
    assert "time range" in str(caught.value)


def test_calculation_is_deterministic_and_does_not_reorder_input() -> None:
    later = sample(10, observed_at=BASE_TIME + timedelta(days=2), source_record_id="z")
    same_time_second = sample(5, observed_at=BASE_TIME, source_record_id="b")
    same_time_first = sample(1, observed_at=BASE_TIME, source_record_id="a")
    samples = (later, same_time_second, same_time_first)
    original = tuple(samples)
    calculator = PersonalBaselineCalculator()

    first = calculator.calculate(PROFILE_ID, MetricIdentifier.STEPS, samples)
    second = calculator.calculate(PROFILE_ID, MetricIdentifier.STEPS, tuple(reversed(samples)))

    assert first == second
    assert first.first_observed_at == BASE_TIME
    assert first.last_observed_at == BASE_TIME + timedelta(days=2)
    assert samples == original


def test_same_timestamp_source_identifier_tie_break_is_deterministic() -> None:
    earlier_offset = datetime(2026, 2, 1, 13, 30, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    utc_equivalent = datetime(2026, 2, 1, 8, tzinfo=UTC)
    samples = (
        sample(2, observed_at=earlier_offset, source_record_id="z"),
        sample(1, observed_at=utc_equivalent, source_record_id="a"),
    )

    baseline = PersonalBaselineCalculator().calculate(
        PROFILE_ID,
        MetricIdentifier.STEPS,
        samples,
    )

    assert baseline.first_observed_at is utc_equivalent
    assert baseline.last_observed_at is earlier_offset


@pytest.mark.parametrize("profile_id", [None, PROFILE_ID.value, RecordId("wrong")])
def test_calculate_validates_profile_before_other_arguments(profile_id: object) -> None:
    with pytest.raises(AnalyticsValidationError, match="profile_id"):
        PersonalBaselineCalculator().calculate(profile_id, "steps", [])  # type: ignore[arg-type]


@pytest.mark.parametrize("metric", [None, "steps", MeasurementUnit.COUNT])
def test_calculate_rejects_invalid_metric(metric: object) -> None:
    with pytest.raises(AnalyticsValidationError, match="metric"):
        PersonalBaselineCalculator().calculate(PROFILE_ID, metric, ())  # type: ignore[arg-type]


@pytest.mark.parametrize("samples", [[], {}, None, iter(())])
def test_calculate_requires_exact_tuple(samples: object) -> None:
    with pytest.raises(AnalyticsValidationError, match="samples"):
        PersonalBaselineCalculator().calculate(
            PROFILE_ID,
            MetricIdentifier.STEPS,
            samples,  # type: ignore[arg-type]
        )


def test_calculate_validates_time_range_before_sample_elements() -> None:
    with pytest.raises(AnalyticsValidationError, match="time_range"):
        PersonalBaselineCalculator().calculate(
            PROFILE_ID,
            MetricIdentifier.STEPS,
            (object(),),  # type: ignore[arg-type]
            time_range="today",  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("bad_sample", [None, {}, object()])
def test_calculate_rejects_invalid_sample_elements(bad_sample: object) -> None:
    with pytest.raises(AnalyticsValidationError, match="every sample"):
        PersonalBaselineCalculator().calculate(
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
        PersonalBaselineCalculator().calculate(
            PROFILE_ID,
            MetricIdentifier.STEPS,
            (derived,),
        )


def test_calculator_defensively_rejects_noncanonical_retained_unit() -> None:
    malformed = sample(1)
    object.__setattr__(malformed, "unit", MeasurementUnit.HOURS)

    with pytest.raises(AnalyticsValidationError, match="canonical unit"):
        PersonalBaselineCalculator().calculate(
            PROFILE_ID,
            MetricIdentifier.STEPS,
            (malformed,),
        )


@pytest.mark.parametrize(
    ("records", "metric", "expected_mean"),
    [
        (
            (sleep_record("s1", minutes=360), sleep_record("s2", hour=1, minutes=480)),
            MetricIdentifier.SLEEP_DURATION,
            7.0,
        ),
        (
            (hydration_record("h1", volume=250), hydration_record("h2", hour=1, volume=750)),
            MetricIdentifier.WATER_INTAKE,
            500.0,
        ),
        ((activity_record(),), MetricIdentifier.STEPS, 8000.0),
        ((body_record(),), MetricIdentifier.WEIGHT, 72.5),
        ((checkin(),), MetricIdentifier.MOOD_SCORE, 7.0),
    ],
)
def test_calculate_from_records_uses_shared_statistics(
    records: tuple[object, ...],
    metric: MetricIdentifier,
    expected_mean: float,
) -> None:
    baseline = PersonalBaselineCalculator().calculate_from_records(
        PROFILE_ID,
        metric,
        records,  # type: ignore[arg-type]
    )

    assert baseline.profile_id is PROFILE_ID
    assert baseline.metric is metric
    assert baseline.mean == expected_mean


def test_calculate_from_records_filters_time_and_unselected_record_metrics() -> None:
    requested_range = TimeRange(BASE_TIME, BASE_TIME + timedelta(hours=2))
    records = (
        hydration_record("start", hour=0, volume=200),
        activity_record("other-kind", hour=1),
        hydration_record("inside", hour=1, volume=600),
        hydration_record("end", hour=2, volume=1000),
    )

    baseline = PersonalBaselineCalculator().calculate_from_records(
        PROFILE_ID,
        MetricIdentifier.WATER_INTAKE,
        records,
        time_range=requested_range,
    )

    assert baseline.sample_count == 2
    assert baseline.mean == 400.0
    assert baseline.time_range is requested_range


@pytest.mark.parametrize(
    "records, metric",
    [
        ((), MetricIdentifier.STEPS),
        ((meal_record(),), MetricIdentifier.CALORIES),
        ((bleeding_record(), cycle_record()), MetricIdentifier.STEPS),
    ],
)
def test_calculate_from_records_raises_when_extraction_has_no_selected_data(
    records: tuple[object, ...],
    metric: MetricIdentifier,
) -> None:
    with pytest.raises(InsufficientBaselineDataError):
        PersonalBaselineCalculator().calculate_from_records(
            PROFILE_ID,
            metric,
            records,  # type: ignore[arg-type]
        )


def test_calculate_from_records_is_repeatable_and_preserves_records_tuple() -> None:
    records = (hydration_record("b", hour=1), hydration_record("a", hour=0))
    original = tuple(records)
    calculator = PersonalBaselineCalculator()

    assert calculator.calculate_from_records(
        PROFILE_ID, MetricIdentifier.WATER_INTAKE, records
    ) == calculator.calculate_from_records(PROFILE_ID, MetricIdentifier.WATER_INTAKE, records)
    assert records == original


@pytest.mark.parametrize("profile_id", [None, PROFILE_ID.value, RecordId("wrong")])
def test_calculate_from_records_validates_profile_first(profile_id: object) -> None:
    with pytest.raises(AnalyticsValidationError, match="profile_id"):
        PersonalBaselineCalculator().calculate_from_records(
            profile_id,  # type: ignore[arg-type]
            "steps",  # type: ignore[arg-type]
            [],  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("metric", [None, "steps", MeasurementUnit.COUNT])
def test_calculate_from_records_rejects_invalid_metric(metric: object) -> None:
    with pytest.raises(AnalyticsValidationError, match="metric"):
        PersonalBaselineCalculator().calculate_from_records(
            PROFILE_ID,
            metric,  # type: ignore[arg-type]
            (),
        )


@pytest.mark.parametrize("records", [[], {}, None, iter(())])
def test_calculate_from_records_requires_exact_tuple(records: object) -> None:
    with pytest.raises(AnalyticsValidationError, match="records"):
        PersonalBaselineCalculator().calculate_from_records(
            PROFILE_ID,
            MetricIdentifier.STEPS,
            records,  # type: ignore[arg-type]
        )


def test_calculate_from_records_validates_time_range_before_record_elements() -> None:
    with pytest.raises(AnalyticsValidationError, match="time_range"):
        PersonalBaselineCalculator().calculate_from_records(
            PROFILE_ID,
            MetricIdentifier.STEPS,
            (object(),),  # type: ignore[arg-type]
            time_range="today",  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("record", [None, {}, object()])
def test_calculate_from_records_rejects_invalid_record_elements(record: object) -> None:
    with pytest.raises(AnalyticsValidationError, match="record"):
        PersonalBaselineCalculator().calculate_from_records(
            PROFILE_ID,
            MetricIdentifier.STEPS,
            (record,),  # type: ignore[arg-type]
        )


def test_calculate_from_records_rejects_record_subclass() -> None:
    base = sleep_record()
    derived = SleepRecordSubclass(
        base.metadata,
        base.period,
        base.sleep_minutes,
        base.awake_minutes,
    )

    with pytest.raises(AnalyticsValidationError, match="exact supported"):
        PersonalBaselineCalculator().calculate_from_records(
            PROFILE_ID,
            MetricIdentifier.SLEEP_DURATION,
            (derived,),
        )


def test_public_analytics_api_is_exact_deterministic_and_isolated() -> None:
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
    assert len(lifelenz.analytics.__all__) == len(set(lifelenz.analytics.__all__))
    assert lifelenz.analytics.__all__ == sorted(lifelenz.analytics.__all__)
    assert all(hasattr(lifelenz.analytics, name) for name in expected)
    assert not set(expected) & set(lifelenz.domain.__all__)
    assert not set(expected) & set(lifelenz.repositories.__all__)
    assert not set(expected) & set(lifelenz.application.__all__)
    assert len(lifelenz.domain.__all__) == 48
    assert len(lifelenz.repositories.__all__) == 11
    assert len(lifelenz.application.__all__) == 8


def test_analytics_dependency_direction_and_runtime_scope() -> None:
    root = Path(__file__).parents[3]
    production = root / "src" / "lifelenz"
    analytics_sources = "\n".join(
        path.read_text(encoding="utf-8") for path in (production / "analytics").glob("*.py")
    )

    for layer in ("domain", "repositories", "application"):
        sources = "\n".join(
            path.read_text(encoding="utf-8") for path in (production / layer).glob("*.py")
        )
        assert "lifelenz.analytics" not in sources

    assert "lifelenz.repositories" not in analytics_sources
    assert "lifelenz.application" not in analytics_sources
    for forbidden in (
        "import pandas",
        "import numpy",
        "datetime.now",
        "datetime.today",
        "random.",
        "async def",
    ):
        assert forbidden not in analytics_sources
