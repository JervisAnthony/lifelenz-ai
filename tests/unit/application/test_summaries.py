"""Behavior tests for the structured wellness-summary application workflow."""

import inspect
from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime, timedelta
from math import inf, nan
from pathlib import Path

import pytest

import lifelenz.analytics
import lifelenz.application
import lifelenz.application.summaries as summaries_module
import lifelenz.domain
import lifelenz.repositories
from lifelenz.analytics import (
    AnalyticsValidationError,
    MetricSample,
    PersonalBaseline,
    PersonalBaselineCalculator,
    TrendDirection,
    WellnessTrend,
    WellnessTrendCalculator,
)
from lifelenz.application import (
    ApplicationValidationError,
    MetricWellnessSummary,
    ProfileNotFoundError,
    WellnessSummary,
    WellnessSummaryService,
    WellnessSummaryUnavailableError,
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
    WellnessProfile,
    WorkoutRecord,
    WorkoutType,
)
from lifelenz.domain.taxonomy import DEFAULT_UNIT_BY_METRIC
from lifelenz.repositories import (
    EntityNotFoundError,
    InMemoryProfileRepository,
    InMemoryWellnessRecordRepository,
    RepositoryError,
)

PROFILE_ID = ProfileId("30000000-0000-4000-8000-000000000001")
OTHER_PROFILE_ID = ProfileId("30000000-0000-4000-8000-000000000002")
BASE_TIME = datetime(2026, 8, 1, 8, tzinfo=UTC)


def profile(profile_id: ProfileId = PROFILE_ID) -> WellnessProfile:
    return WellnessProfile(profile_id, "UTC", display_name="Summary profile")


def metadata(record_id: str, *, day: float = 0) -> RecordMetadata:
    return RecordMetadata(
        RecordId(record_id),
        BASE_TIME + timedelta(days=day),
        DataSource.MANUAL,
    )


def hydration(record_id: str, value: int | float = 250, *, day: float = 0) -> HydrationRecord:
    return HydrationRecord(metadata(record_id, day=day), value, BeverageType.WATER)


def sleep(record_id: str, minutes: int = 420, *, day: float = 0) -> SleepRecord:
    observed = BASE_TIME + timedelta(days=day)
    return SleepRecord(
        metadata(record_id, day=day),
        TimeRange(observed - timedelta(hours=8), observed),
        sleep_minutes=minutes,
        awake_minutes=0,
    )


def activity(record_id: str, steps: int = 1000, *, day: float = 0) -> DailyActivityRecord:
    return DailyActivityRecord(
        metadata(record_id, day=day),
        date(2026, 8, 1),
        steps=steps,
        distance_kilometers=5,
        active_minutes=30,
        active_calories_kcal=200,
    )


def workout(record_id: str, minutes: int = 60, *, day: float = 0) -> WorkoutRecord:
    observed = BASE_TIME + timedelta(days=day)
    return WorkoutRecord(
        metadata(record_id, day=day),
        TimeRange(observed - timedelta(minutes=minutes), observed),
        WorkoutType.WALKING,
    )


def nutrition(record_id: str, calories: int = 1800, *, day: float = 0) -> DailyNutritionRecord:
    return DailyNutritionRecord(
        metadata(record_id, day=day),
        date(2026, 8, 1),
        MealNutrition(calories_kcal=calories),
        meal_count=3,
    )


def body(record_id: str, weight: int | float = 70, *, day: float = 0) -> BodyMeasurementRecord:
    return BodyMeasurementRecord(metadata(record_id, day=day), weight_kilograms=weight)


def checkin(record_id: str, mood: int = 5, *, day: float = 0) -> SubjectiveWellnessCheckIn:
    return SubjectiveWellnessCheckIn(
        metadata(record_id, day=day),
        SubjectiveScore(mood),
        SubjectiveScore(6),
        SubjectiveScore(4),
    )


def meal(record_id: str, *, day: float = 0) -> MealRecord:
    return MealRecord(
        metadata(record_id, day=day),
        MealType.LUNCH,
        MealNutrition(calories_kcal=500),
    )


def bleeding(record_id: str) -> MenstrualBleedingRecord:
    return MenstrualBleedingRecord(metadata(record_id), MenstrualFlow.LIGHT)


def cycle(record_id: str) -> MenstrualCycleRecord:
    return MenstrualCycleRecord(metadata(record_id), date(2026, 8, 1), date(2026, 8, 4))


def sample(
    value: int | float,
    *,
    metric: MetricIdentifier = MetricIdentifier.STEPS,
    day: float = 0,
    sample_id: str = "sample",
    owner: ProfileId = PROFILE_ID,
) -> MetricSample:
    return MetricSample(
        owner,
        metric,
        value,
        DEFAULT_UNIT_BY_METRIC[metric],
        BASE_TIME + timedelta(days=day),
        RecordId(sample_id),
    )


def analytics_pair(
    *,
    metric: MetricIdentifier = MetricIdentifier.STEPS,
    owner: ProfileId = PROFILE_ID,
    time_range: TimeRange | None = None,
) -> tuple[PersonalBaseline, WellnessTrend]:
    samples = (
        sample(10, metric=metric, sample_id="first", owner=owner),
        sample(20, metric=metric, day=1, sample_id="last", owner=owner),
    )
    baseline = PersonalBaselineCalculator().calculate(owner, metric, samples, time_range=time_range)
    trend = WellnessTrendCalculator().calculate(owner, metric, samples, time_range=time_range)
    return baseline, trend


def one_sample_baseline(
    *,
    metric: MetricIdentifier = MetricIdentifier.STEPS,
    owner: ProfileId = PROFILE_ID,
    time_range: TimeRange | None = None,
) -> PersonalBaseline:
    return PersonalBaselineCalculator().calculate(
        owner,
        metric,
        (sample(10, metric=metric, sample_id="only", owner=owner),),
        time_range=time_range,
    )


def metric_summary(
    *,
    metric: MetricIdentifier = MetricIdentifier.STEPS,
    owner: ProfileId = PROFILE_ID,
    time_range: TimeRange | None = None,
    with_trend: bool = True,
) -> MetricWellnessSummary:
    if with_trend:
        baseline, trend = analytics_pair(metric=metric, owner=owner, time_range=time_range)
    else:
        baseline = one_sample_baseline(metric=metric, owner=owner, time_range=time_range)
        trend = None
    return MetricWellnessSummary(metric, DEFAULT_UNIT_BY_METRIC[metric], baseline, trend)


def service_with(*records: object) -> WellnessSummaryService:
    profiles = InMemoryProfileRepository()
    repository = InMemoryWellnessRecordRepository()
    profiles.save(profile())
    for record in records:
        repository.save(PROFILE_ID, record)  # type: ignore[arg-type]
    return WellnessSummaryService(profiles, repository)


def test_metric_summary_preserves_models_and_direct_properties() -> None:
    baseline, trend = analytics_pair()
    result = MetricWellnessSummary(MetricIdentifier.STEPS, MeasurementUnit.COUNT, baseline, trend)

    assert result.baseline is baseline
    assert result.trend is trend
    assert result.profile_id is PROFILE_ID
    assert result.sample_count == 2
    assert result.has_trend is True
    assert result.first_observed_at == BASE_TIME
    assert result.last_observed_at == BASE_TIME + timedelta(days=1)
    assert result.observation_span == timedelta(days=1)
    assert result == metric_summary()
    assert hash(result) == hash(metric_summary())
    with pytest.raises((FrozenInstanceError, AttributeError)):
        result.trend = None  # type: ignore[misc]


def test_metric_summary_one_sample_has_baseline_without_trend() -> None:
    result = metric_summary(with_trend=False)

    assert result.sample_count == 1
    assert result.has_trend is False
    assert result.trend is None
    assert result.observation_span == timedelta(0)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("metric", "steps", "metric"),
        ("unit", "count", "unit"),
        ("unit", MeasurementUnit.KILOMETERS, "canonical"),
        ("baseline", {}, "baseline"),
        ("trend", {}, "trend"),
    ],
)
def test_metric_summary_rejects_untyped_or_noncanonical_fields(
    field: str, value: object, message: str
) -> None:
    baseline, trend = analytics_pair()
    values = {
        "metric": MetricIdentifier.STEPS,
        "unit": MeasurementUnit.COUNT,
        "baseline": baseline,
        "trend": trend,
    }
    values[field] = value
    with pytest.raises(ApplicationValidationError, match=message):
        MetricWellnessSummary(**values)  # type: ignore[arg-type]


def test_metric_summary_rejects_baseline_metric_and_unit_mismatches() -> None:
    baseline, trend = analytics_pair(metric=MetricIdentifier.DISTANCE)
    with pytest.raises(ApplicationValidationError, match="baseline metric"):
        MetricWellnessSummary(MetricIdentifier.STEPS, MeasurementUnit.COUNT, baseline, trend)

    malformed = object.__new__(PersonalBaseline)
    for field, value in {
        "profile_id": PROFILE_ID,
        "metric": MetricIdentifier.STEPS,
        "unit": MeasurementUnit.KILOMETERS,
        "sample_count": 1,
    }.items():
        object.__setattr__(malformed, field, value)
    with pytest.raises(ApplicationValidationError, match="baseline unit"):
        MetricWellnessSummary(MetricIdentifier.STEPS, MeasurementUnit.COUNT, malformed, None)


def test_metric_summary_requires_trend_for_multiple_samples() -> None:
    baseline, _ = analytics_pair()
    with pytest.raises(ApplicationValidationError, match="trend may be None"):
        MetricWellnessSummary(MetricIdentifier.STEPS, MeasurementUnit.COUNT, baseline, None)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"profile_id": OTHER_PROFILE_ID}, "profile_id"),
        ({"metric": MetricIdentifier.DISTANCE, "unit": MeasurementUnit.KILOMETERS}, "trend metric"),
        ({"unit": MeasurementUnit.KILOMETERS}, "trend unit"),
        ({"sample_count": 3}, "sample_count"),
    ],
)
def test_metric_summary_rejects_trend_identity_and_count_mismatches(
    change: dict[str, object], message: str
) -> None:
    baseline, trend = analytics_pair()
    malformed = object.__new__(WellnessTrend)
    for field in WellnessTrend.__dataclass_fields__:
        object.__setattr__(malformed, field, change.get(field, getattr(trend, field)))
    with pytest.raises(ApplicationValidationError, match=message):
        MetricWellnessSummary(MetricIdentifier.STEPS, MeasurementUnit.COUNT, baseline, malformed)


def test_metric_summary_rejects_trend_range_and_observation_bound_mismatches() -> None:
    baseline, trend = analytics_pair()
    ranged = object.__new__(WellnessTrend)
    for field in WellnessTrend.__dataclass_fields__:
        value = (
            TimeRange(BASE_TIME, BASE_TIME + timedelta(days=2))
            if field == "time_range"
            else getattr(trend, field)
        )
        object.__setattr__(ranged, field, value)
    with pytest.raises(ApplicationValidationError, match="time_range"):
        MetricWellnessSummary(MetricIdentifier.STEPS, MeasurementUnit.COUNT, baseline, ranged)

    for field, value in (
        ("first_observed_at", BASE_TIME - timedelta(seconds=1)),
        ("last_observed_at", BASE_TIME + timedelta(days=2)),
    ):
        malformed = object.__new__(WellnessTrend)
        for trend_field in WellnessTrend.__dataclass_fields__:
            object.__setattr__(
                malformed,
                trend_field,
                value if trend_field == field else getattr(trend, trend_field),
            )
        with pytest.raises(ApplicationValidationError, match="observation bounds"):
            MetricWellnessSummary(
                MetricIdentifier.STEPS, MeasurementUnit.COUNT, baseline, malformed
            )


def test_metric_summary_exposes_no_interpretive_properties() -> None:
    result = metric_summary()
    for name in (
        "recommendation",
        "health_status",
        "is_healthy",
        "is_improving",
        "risk",
        "score",
        "goal_progress",
        "predicted_value",
    ):
        assert not hasattr(result, name)


def test_wellness_summary_preserves_order_profile_and_derived_properties() -> None:
    first = metric_summary(metric=MetricIdentifier.ACTIVE_MINUTES, with_trend=False)
    second = metric_summary(metric=MetricIdentifier.STEPS)
    result = WellnessSummary(profile(), (first, second), None, 4)

    assert result.profile is not None
    assert result.profile_id is PROFILE_ID
    assert result.metrics == (first, second)
    assert result.metric_count == 2
    assert result.metrics_with_trends == (second,)
    assert result.metrics_without_trends == (first,)
    assert result.first_observed_at == BASE_TIME
    assert result.last_observed_at == BASE_TIME + timedelta(days=1)
    assert result.observation_span == timedelta(days=1)
    assert result == WellnessSummary(profile(), (first, second), None, 4)
    assert hash(result) == hash(WellnessSummary(profile(), (first, second), None, 4))
    with pytest.raises((FrozenInstanceError, AttributeError)):
        result.metrics = ()  # type: ignore[misc]


@pytest.mark.parametrize("invalid", [None, PROFILE_ID, {}, object()])
def test_wellness_summary_rejects_invalid_profile(invalid: object) -> None:
    with pytest.raises(ApplicationValidationError, match="profile"):
        WellnessSummary(invalid, (metric_summary(),), None, 1)  # type: ignore[arg-type]


@pytest.mark.parametrize("invalid", [[], set(), {}, "metrics", iter(())])
def test_wellness_summary_requires_exact_metric_tuple(invalid: object) -> None:
    with pytest.raises(ApplicationValidationError, match="metrics"):
        WellnessSummary(profile(), invalid, None, 1)  # type: ignore[arg-type]


def test_wellness_summary_rejects_empty_invalid_duplicate_and_out_of_order_metrics() -> None:
    with pytest.raises(ApplicationValidationError, match="at least one"):
        WellnessSummary(profile(), (), None, 1)
    with pytest.raises(ApplicationValidationError, match="exact MetricWellnessSummary"):
        WellnessSummary(profile(), (object(),), None, 1)  # type: ignore[arg-type]
    item = metric_summary()
    with pytest.raises(ApplicationValidationError, match="duplicate"):
        WellnessSummary(profile(), (item, item), None, 1)
    earlier = metric_summary(metric=MetricIdentifier.ACTIVE_MINUTES, with_trend=False)
    with pytest.raises(ApplicationValidationError, match="ordered"):
        WellnessSummary(profile(), (item, earlier), None, 1)


def test_wellness_summary_rejects_owner_and_time_range_mismatches() -> None:
    with pytest.raises(ApplicationValidationError, match="belong"):
        WellnessSummary(profile(), (metric_summary(owner=OTHER_PROFILE_ID),), None, 1)
    requested = TimeRange(BASE_TIME, BASE_TIME + timedelta(days=2))
    with pytest.raises(ApplicationValidationError, match="time_range"):
        WellnessSummary(profile(), (metric_summary(with_trend=False),), requested, 1)


@pytest.mark.parametrize("invalid", ["range", (), {}, date(2026, 8, 1), object()])
def test_wellness_summary_rejects_invalid_time_range(invalid: object) -> None:
    with pytest.raises(ApplicationValidationError, match="time_range"):
        WellnessSummary(profile(), (metric_summary(),), invalid, 1)  # type: ignore[arg-type]


@pytest.mark.parametrize("invalid", [True, False, 0, -1, 1.0, "1", None])
def test_wellness_summary_rejects_invalid_record_count(invalid: object) -> None:
    with pytest.raises(ApplicationValidationError, match="generated_from_record_count"):
        WellnessSummary(profile(), (metric_summary(),), None, invalid)  # type: ignore[arg-type]


def test_wellness_summary_exposes_no_interpretive_properties() -> None:
    result = WellnessSummary(profile(), (metric_summary(),), None, 1)
    for name in (
        "health_score",
        "readiness_score",
        "risk_score",
        "overall_status",
        "recommendations",
        "concern_count",
        "positive_trend_count",
        "goal_progress",
        "generated_at",
    ):
        assert not hasattr(result, name)


@pytest.mark.parametrize(
    "invalid_profile_repository,invalid_record_repository",
    [
        (None, InMemoryWellnessRecordRepository()),
        (object(), InMemoryWellnessRecordRepository()),
        (InMemoryWellnessRecordRepository(), InMemoryWellnessRecordRepository()),
        (InMemoryProfileRepository(), None),
        (InMemoryProfileRepository(), object()),
        (InMemoryProfileRepository(), InMemoryProfileRepository()),
    ],
)
def test_service_rejects_invalid_or_swapped_repository_dependencies(
    invalid_profile_repository: object, invalid_record_repository: object
) -> None:
    with pytest.raises(ApplicationValidationError):
        WellnessSummaryService(invalid_profile_repository, invalid_record_repository)  # type: ignore[arg-type]


def test_service_accepts_independent_in_memory_repositories_and_stores_them_privately() -> None:
    profiles = InMemoryProfileRepository()
    records = InMemoryWellnessRecordRepository()
    first = WellnessSummaryService(profiles, records)
    second = WellnessSummaryService(profiles, records)

    assert first is not second
    assert first._profile_repository is profiles
    assert first._record_repository is records
    assert not hasattr(first, "profile_repository")
    assert not hasattr(first, "record_repository")


class StructuralProfileRepository:
    def __init__(self, stored_profile: WellnessProfile) -> None:
        self.stored_profile = stored_profile

    def save(self, profile: WellnessProfile) -> None:
        self.stored_profile = profile

    def get(self, profile_id: ProfileId) -> WellnessProfile:
        return self.stored_profile

    def exists(self, profile_id: ProfileId) -> bool:
        return profile_id == self.stored_profile.profile_id

    def list_all(self) -> tuple[WellnessProfile, ...]:
        return (self.stored_profile,)

    def remove(self, profile_id: ProfileId) -> None:
        return None


class StructuralRecordRepository:
    def __init__(self, stored_record: object) -> None:
        self.stored_record = stored_record

    def save(self, profile_id: ProfileId, record: object) -> None:
        self.stored_record = record

    def get(self, profile_id: ProfileId, record_id: RecordId) -> object:
        return self.stored_record

    def exists(self, profile_id: ProfileId, record_id: RecordId) -> bool:
        return True

    def list_for_profile(self, profile_id: ProfileId) -> tuple[object, ...]:
        return (self.stored_record,)

    def list_in_time_range(
        self, profile_id: ProfileId, time_range: TimeRange
    ) -> tuple[object, ...]:
        return (self.stored_record,)

    def list_by_type(self, profile_id: ProfileId, record_type: object) -> tuple[object, ...]:
        return (self.stored_record,)

    def list_by_type_in_time_range(
        self,
        profile_id: ProfileId,
        record_type: object,
        time_range: TimeRange,
    ) -> tuple[object, ...]:
        return (self.stored_record,)

    def remove(self, profile_id: ProfileId, record_id: RecordId) -> None:
        return None


def test_service_accepts_structurally_compatible_non_in_memory_repositories() -> None:
    service = WellnessSummaryService(
        StructuralProfileRepository(profile()),
        StructuralRecordRepository(hydration("structural")),  # type: ignore[arg-type]
    )
    result = service.create_summary(PROFILE_ID)

    assert result.profile_id is PROFILE_ID
    assert result.generated_from_record_count == 1


@pytest.mark.parametrize("invalid", [None, PROFILE_ID.value, RecordId("profile"), {}, object()])
def test_create_summary_rejects_invalid_profile_id_before_repository_calls(invalid: object) -> None:
    service = WellnessSummaryService(FailingProfileRepository(), FailingRecordRepository())
    with pytest.raises(ApplicationValidationError, match="profile_id"):
        service.create_summary(invalid)  # type: ignore[arg-type]


@pytest.mark.parametrize("invalid", ["range", (), {}, date(2026, 8, 1), object()])
def test_create_summary_rejects_invalid_time_range_before_repository_calls(invalid: object) -> None:
    service = WellnessSummaryService(FailingProfileRepository(), FailingRecordRepository())
    with pytest.raises(ApplicationValidationError, match="time_range"):
        service.create_summary(PROFILE_ID, time_range=invalid)  # type: ignore[arg-type]


@pytest.mark.parametrize("invalid", [True, False, -1, nan, inf, -inf, "0", None, 10**1000])
def test_create_summary_rejects_invalid_tolerance_before_repository_calls(invalid: object) -> None:
    service = WellnessSummaryService(FailingProfileRepository(), FailingRecordRepository())
    with pytest.raises(ApplicationValidationError, match="trend_stability_tolerance"):
        service.create_summary(PROFILE_ID, trend_stability_tolerance=invalid)  # type: ignore[arg-type]


class FailingProfileRepository(InMemoryProfileRepository):
    def get(self, profile_id: ProfileId) -> WellnessProfile:
        raise AssertionError("profile repository must not be called")


class FailingRecordRepository(InMemoryWellnessRecordRepository):
    def list_for_profile(self, profile_id: ProfileId) -> tuple[object, ...]:
        raise AssertionError("record repository must not be called")

    def list_in_time_range(
        self, profile_id: ProfileId, time_range: TimeRange
    ) -> tuple[object, ...]:
        raise AssertionError("record repository must not be called")


class ErrorProfileRepository(InMemoryProfileRepository):
    def __init__(self, error: Exception) -> None:
        super().__init__()
        self.error = error

    def get(self, profile_id: ProfileId) -> WellnessProfile:
        raise self.error


class ErrorRecordRepository(InMemoryWellnessRecordRepository):
    def __init__(self, error: Exception) -> None:
        super().__init__()
        self.error = error

    def list_for_profile(self, profile_id: ProfileId) -> tuple[object, ...]:
        raise self.error


def test_missing_profile_is_translated_with_chaining_and_skips_records() -> None:
    cause = EntityNotFoundError("missing")
    service = WellnessSummaryService(ErrorProfileRepository(cause), FailingRecordRepository())

    with pytest.raises(ProfileNotFoundError, match=PROFILE_ID.value) as caught:
        service.create_summary(PROFILE_ID)
    assert caught.value.__cause__ is cause


@pytest.mark.parametrize("error", [RepositoryError("failure"), RuntimeError("boom")])
def test_profile_repository_non_absence_errors_propagate(error: Exception) -> None:
    with pytest.raises(type(error)) as caught:
        WellnessSummaryService(
            ErrorProfileRepository(error), FailingRecordRepository()
        ).create_summary(PROFILE_ID)
    assert caught.value is error


@pytest.mark.parametrize("error", [RepositoryError("failure"), RuntimeError("boom")])
def test_record_repository_errors_propagate(error: Exception) -> None:
    profiles = InMemoryProfileRepository()
    profiles.save(profile())
    with pytest.raises(type(error)) as caught:
        WellnessSummaryService(profiles, ErrorRecordRepository(error)).create_summary(PROFILE_ID)
    assert caught.value is error


@pytest.mark.parametrize(
    "records",
    [
        (),
        (meal("meal"),),
        (bleeding("bleeding"),),
        (cycle("cycle"),),
        (meal("meal"), bleeding("bleeding"), cycle("cycle")),
    ],
)
def test_existing_profile_without_extractable_summary_data_is_explicitly_unavailable(
    records: tuple[object, ...],
) -> None:
    service = service_with(*records)
    with pytest.raises(WellnessSummaryUnavailableError, match=PROFILE_ID.value):
        service.create_summary(PROFILE_ID)


@pytest.mark.parametrize(
    ("record", "expected_metric"),
    [
        (sleep("sleep"), MetricIdentifier.SLEEP_DURATION),
        (activity("activity"), MetricIdentifier.STEPS),
        (hydration("hydration"), MetricIdentifier.WATER_INTAKE),
        (nutrition("nutrition"), MetricIdentifier.CALORIES),
        (body("body"), MetricIdentifier.WEIGHT),
        (checkin("checkin"), MetricIdentifier.MOOD_SCORE),
        (workout("workout"), MetricIdentifier.ACTIVE_MINUTES),
    ],
)
def test_one_record_categories_produce_canonical_baselines_without_trends(
    record: object, expected_metric: MetricIdentifier
) -> None:
    result = service_with(record).create_summary(PROFILE_ID)
    selected = next(summary for summary in result.metrics if summary.metric is expected_metric)

    assert selected.sample_count == 1
    assert selected.trend is None
    assert selected.unit is DEFAULT_UNIT_BY_METRIC[expected_metric]
    assert selected.first_observed_at == record.metadata.recorded_at  # type: ignore[attr-defined]
    assert result.generated_from_record_count == 1


@pytest.mark.parametrize(
    ("records", "metric", "expected_change"),
    [
        ((sleep("a", 360), sleep("b", 480, day=1)), MetricIdentifier.SLEEP_DURATION, 2.0),
        ((activity("a", 1000), activity("b", 1300, day=1)), MetricIdentifier.STEPS, 300.0),
        ((hydration("a", 200), hydration("b", 300, day=1)), MetricIdentifier.WATER_INTAKE, 100.0),
        ((nutrition("a", 1800), nutrition("b", 2000, day=1)), MetricIdentifier.CALORIES, 200.0),
        ((body("a", 70), body("b", 71, day=1)), MetricIdentifier.WEIGHT, 1.0),
        ((checkin("a", 5), checkin("b", 7, day=1)), MetricIdentifier.MOOD_SCORE, 2.0),
        ((workout("a", 30), workout("b", 60, day=1)), MetricIdentifier.ACTIVE_MINUTES, 30.0),
    ],
)
def test_multi_sample_categories_include_matching_baseline_and_trend(
    records: tuple[object, object], metric: MetricIdentifier, expected_change: float
) -> None:
    result = service_with(*records).create_summary(PROFILE_ID)
    selected = next(summary for summary in result.metrics if summary.metric is metric)

    assert selected.trend is not None
    assert selected.sample_count == selected.trend.sample_count == 2
    assert selected.trend.absolute_change == expected_change
    assert selected.trend.profile_id == selected.baseline.profile_id == PROFILE_ID
    assert selected.trend.metric is selected.baseline.metric is metric
    assert selected.trend.unit is selected.baseline.unit is DEFAULT_UNIT_BY_METRIC[metric]


def test_mixed_records_include_every_metric_once_in_explicit_order() -> None:
    records = (
        hydration("hydration"),
        sleep("sleep-b", 480, day=1),
        body("body"),
        activity("activity-b", 2000, day=1),
        checkin("checkin"),
        sleep("sleep-a", 420),
        meal("meal"),
        activity("activity-a", 1000),
    )
    result = service_with(*reversed(records)).create_summary(PROFILE_ID)

    identifiers = tuple(summary.metric for summary in result.metrics)
    assert identifiers == tuple(sorted(set(identifiers), key=lambda metric: metric.value))
    assert len(identifiers) == len(set(identifiers))
    assert result.generated_from_record_count == len(records)
    assert {summary.metric for summary in result.metrics_with_trends} >= {
        MetricIdentifier.SLEEP_DURATION,
        MetricIdentifier.STEPS,
    }
    assert {summary.metric for summary in result.metrics_without_trends} >= {
        MetricIdentifier.WATER_INTAKE,
        MetricIdentifier.WEIGHT,
    }


class ListingSpyRepository(InMemoryWellnessRecordRepository):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[str, object]] = []

    def list_for_profile(self, profile_id: ProfileId) -> tuple[object, ...]:
        self.calls.append(("list_for_profile", profile_id))
        return super().list_for_profile(profile_id)

    def list_in_time_range(
        self, profile_id: ProfileId, time_range: TimeRange
    ) -> tuple[object, ...]:
        self.calls.append(("list_in_time_range", time_range))
        return super().list_in_time_range(profile_id, time_range)


def test_time_range_delegates_filtering_and_preserves_start_inclusive_end_exclusive() -> None:
    profiles = InMemoryProfileRepository()
    records = ListingSpyRepository()
    profiles.save(profile())
    for record in (
        hydration("before", day=-1),
        hydration("start", 200),
        hydration("inside", 300, day=1),
        hydration("end", 400, day=2),
        hydration("after", day=3),
    ):
        records.save(PROFILE_ID, record)
    service = WellnessSummaryService(profiles, records)
    requested = TimeRange(BASE_TIME, BASE_TIME + timedelta(days=2))

    ranged = service.create_summary(PROFILE_ID, time_range=requested)
    complete = service.create_summary(PROFILE_ID)

    assert records.calls == [("list_in_time_range", requested), ("list_for_profile", PROFILE_ID)]
    assert ranged.time_range is requested
    assert ranged.generated_from_record_count == 2
    assert ranged.metrics[0].sample_count == 2
    assert ranged.metrics[0].baseline.time_range is requested
    assert ranged.metrics[0].trend is not None
    assert ranged.metrics[0].trend.time_range is requested
    assert complete.generated_from_record_count == 5


def test_empty_time_range_result_reports_context() -> None:
    requested = TimeRange(BASE_TIME + timedelta(days=1), BASE_TIME + timedelta(days=2))
    with pytest.raises(WellnessSummaryUnavailableError, match="TimeRange"):
        service_with(hydration("before", day=-1)).create_summary(PROFILE_ID, time_range=requested)


@pytest.mark.parametrize(
    ("ending", "tolerance", "direction"),
    [
        (10.5, 1.0, TrendDirection.STABLE),
        (9.5, 1.0, TrendDirection.STABLE),
        (12, 1.0, TrendDirection.INCREASING),
        (8, 1.0, TrendDirection.DECREASING),
    ],
)
def test_caller_tolerance_controls_each_trend_without_changing_baselines(
    ending: float, tolerance: float, direction: TrendDirection
) -> None:
    result = service_with(hydration("a", 10), hydration("b", ending, day=1)).create_summary(
        PROFILE_ID, trend_stability_tolerance=tolerance
    )
    summary = result.metrics[0]
    assert summary.baseline.mean == (10 + ending) / 2
    assert summary.trend is not None
    assert summary.trend.stability_tolerance == tolerance
    assert summary.trend.direction is direction


def test_integer_tolerance_is_accepted_and_converted_only_for_analytics() -> None:
    result = service_with(hydration("a", 10), hydration("b", 11, day=1)).create_summary(
        PROFILE_ID,
        trend_stability_tolerance=1,  # type: ignore[arg-type]
    )
    assert result.metrics[0].trend is not None
    assert result.metrics[0].trend.stability_tolerance == 1.0


def test_repeated_calls_are_equal_and_do_not_mutate_profile_or_records() -> None:
    original_profile = profile()
    first_record = hydration("later", 300, day=1)
    second_record = hydration("earlier", 200)
    profiles = InMemoryProfileRepository()
    records = InMemoryWellnessRecordRepository()
    profiles.save(original_profile)
    records.save(PROFILE_ID, first_record)
    records.save(PROFILE_ID, second_record)
    service = WellnessSummaryService(profiles, records)

    first = service.create_summary(PROFILE_ID)
    second = service.create_summary(PROFILE_ID)

    assert first == second
    assert first.profile is original_profile
    assert profiles.get(PROFILE_ID) is original_profile
    assert records.list_for_profile(PROFILE_ID) == (second_record, first_record)


def test_analytics_collaborators_are_delegated_by_sample_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, MetricIdentifier]] = []
    real_baseline = PersonalBaselineCalculator
    real_trend = WellnessTrendCalculator

    class BaselineSpy(real_baseline):
        def calculate(
            self,
            profile_id: ProfileId,
            metric: MetricIdentifier,
            samples: tuple[MetricSample, ...],
            *,
            time_range: TimeRange | None = None,
        ) -> PersonalBaseline:
            calls.append(("baseline", metric))
            return super().calculate(profile_id, metric, samples, time_range=time_range)

    class TrendSpy(real_trend):
        def calculate(
            self,
            profile_id: ProfileId,
            metric: MetricIdentifier,
            samples: tuple[MetricSample, ...],
            *,
            time_range: TimeRange | None = None,
            stability_tolerance: float = 0.0,
        ) -> WellnessTrend:
            calls.append(("trend", metric))
            return super().calculate(
                profile_id,
                metric,
                samples,
                time_range=time_range,
                stability_tolerance=stability_tolerance,
            )

    monkeypatch.setattr(summaries_module, "PersonalBaselineCalculator", BaselineSpy)
    monkeypatch.setattr(summaries_module, "WellnessTrendCalculator", TrendSpy)
    result = service_with(
        hydration("a", 10), hydration("b", 20, day=1), body("body")
    ).create_summary(PROFILE_ID)

    assert sorted(metric.value for kind, metric in calls if kind == "baseline") == sorted(
        summary.metric.value for summary in result.metrics
    )
    assert [metric for kind, metric in calls if kind == "trend"] == [MetricIdentifier.WATER_INTAKE]


def test_analytics_validation_error_from_malformed_repository_data_propagates() -> None:
    class MalformedRecords(InMemoryWellnessRecordRepository):
        def list_for_profile(self, profile_id: ProfileId) -> tuple[object, ...]:
            return (object(),)

    profiles = InMemoryProfileRepository()
    profiles.save(profile())
    with pytest.raises(AnalyticsValidationError):
        WellnessSummaryService(profiles, MalformedRecords()).create_summary(PROFILE_ID)


def test_application_api_and_layer_boundaries_are_exact() -> None:
    expected = [
        "ApplicationError",
        "ApplicationValidationError",
        "GoalNotFoundError",
        "GoalService",
        "MetricWellnessSummary",
        "ProfileNotFoundError",
        "ProfileService",
        "WellnessRecordNotFoundError",
        "WellnessRecordService",
        "WellnessSummary",
        "WellnessSummaryService",
        "WellnessSummaryUnavailableError",
    ]
    assert lifelenz.application.__all__ == expected == sorted(expected)
    assert len(expected) == len(set(expected))
    assert not {"MetricWellnessSummary", "WellnessSummary", "WellnessSummaryService"} & set(
        lifelenz.domain.__all__
    )
    assert not set(expected) & set(lifelenz.repositories.__all__)
    assert not {"MetricWellnessSummary", "WellnessSummary", "WellnessSummaryService"} & set(
        lifelenz.analytics.__all__
    )
    assert len(lifelenz.domain.__all__) == 48
    assert len(lifelenz.repositories.__all__) == 11
    assert len(lifelenz.analytics.__all__) == 11


def test_dependency_direction_and_excluded_runtime_imports() -> None:
    source_root = Path(__file__).parents[3] / "src" / "lifelenz"
    summary_source = (source_root / "application" / "summaries.py").read_text(encoding="utf-8")
    for layer in ("domain", "repositories", "analytics"):
        sources = "\n".join(
            path.read_text(encoding="utf-8") for path in (source_root / layer).glob("*.py")
        )
        assert "lifelenz.application" not in sources
    for forbidden in (
        "InMemory",
        "lifelenz.api",
        "lifelenz.persistence",
        "lifelenz.web",
        "datetime.now",
        "datetime.today",
        "date.today",
        "random",
    ):
        assert forbidden not in summary_source
    assert "lifelenz.analytics" in summary_source
    services_source = (source_root / "application" / "services.py").read_text(encoding="utf-8")
    assert "lifelenz.analytics" not in services_source


def test_public_models_and_service_have_required_docstrings() -> None:
    public_members = (
        MetricWellnessSummary,
        MetricWellnessSummary.profile_id,
        MetricWellnessSummary.sample_count,
        MetricWellnessSummary.has_trend,
        MetricWellnessSummary.first_observed_at,
        MetricWellnessSummary.last_observed_at,
        MetricWellnessSummary.observation_span,
        WellnessSummary,
        WellnessSummary.profile_id,
        WellnessSummary.metric_count,
        WellnessSummary.metrics_with_trends,
        WellnessSummary.metrics_without_trends,
        WellnessSummary.first_observed_at,
        WellnessSummary.last_observed_at,
        WellnessSummary.observation_span,
        WellnessSummaryService,
        WellnessSummaryService.create_summary,
    )
    assert all(inspect.getdoc(member) for member in public_members)
