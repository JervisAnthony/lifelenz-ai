"""Tests for daily physical activity and completed workout domain types."""

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from lifelenz import domain
from lifelenz.domain import (
    ConfidenceLevel,
    DailyActivityRecord,
    DataSource,
    DomainValidationError,
    InsightSeverity,
    InvalidIdentifierError,
    InvalidNumericValueError,
    InvalidTimeRangeError,
    InvalidTimestampError,
    MeasurementUnit,
    MetricIdentifier,
    PerceivedExertion,
    RecordId,
    RecordMetadata,
    SleepQuality,
    SleepRecord,
    SleepStageDurations,
    TimeRange,
    WellnessCategory,
    WorkoutRecord,
    WorkoutType,
)


def _metadata() -> RecordMetadata:
    """Return valid metadata for activity records."""
    return RecordMetadata(
        record_id=RecordId("activity-record-1"),
        recorded_at=datetime(2026, 8, 3, 18, tzinfo=UTC),
        source=DataSource.MANUAL,
        notes="Outdoor session",
    )


def _period(
    minutes: int | float = 60,
    *,
    start: datetime | None = None,
) -> TimeRange:
    """Return a valid workout period with the requested duration."""
    period_start = start or datetime(2026, 8, 3, 6, tzinfo=UTC)
    return TimeRange(period_start, period_start + timedelta(minutes=minutes))


def _daily_record(
    *,
    metadata: RecordMetadata | None = None,
    activity_date: date | None = None,
    steps: int = 0,
    distance_kilometers: int | float = 0.0,
    active_minutes: int | float = 0.0,
    active_calories_kcal: int | float = 0.0,
) -> DailyActivityRecord:
    """Build a daily record while keeping test setup concise."""
    return DailyActivityRecord(
        metadata=metadata or _metadata(),
        activity_date=activity_date or date(2026, 8, 3),
        steps=steps,
        distance_kilometers=distance_kilometers,
        active_minutes=active_minutes,
        active_calories_kcal=active_calories_kcal,
    )


def _workout_record(
    *,
    metadata: RecordMetadata | None = None,
    period: TimeRange | None = None,
    workout_type: WorkoutType = WorkoutType.RUNNING,
    distance_kilometers: int | float | None = None,
    active_calories_kcal: int | float | None = None,
    perceived_exertion: PerceivedExertion | None = None,
    average_heart_rate_bpm: int | float | None = None,
) -> WorkoutRecord:
    """Build a workout record while keeping test setup concise."""
    return WorkoutRecord(
        metadata=metadata or _metadata(),
        period=period or _period(),
        workout_type=workout_type,
        distance_kilometers=distance_kilometers,
        active_calories_kcal=active_calories_kcal,
        perceived_exertion=perceived_exertion,
        average_heart_rate_bpm=average_heart_rate_bpm,
    )


def test_workout_type_has_exact_stable_ordered_members() -> None:
    """Workout types expose the complete vendor-neutral serialized vocabulary."""
    expected = [
        ("WALKING", "walking"),
        ("RUNNING", "running"),
        ("CYCLING", "cycling"),
        ("SWIMMING", "swimming"),
        ("STRENGTH_TRAINING", "strength_training"),
        ("YOGA", "yoga"),
        ("HIKING", "hiking"),
        ("ROWING", "rowing"),
        ("ELLIPTICAL", "elliptical"),
        ("SPORT", "sport"),
        ("OTHER", "other"),
    ]

    assert [(member.name, member.value) for member in WorkoutType] == expected
    assert len({member.value for member in WorkoutType}) == len(expected)
    assert all(str(member) == member.value for member in WorkoutType)


@pytest.mark.parametrize("score", [1, 5, 10])
def test_perceived_exertion_accepts_inclusive_range(score: int) -> None:
    """Minimum, middle, and maximum plain integer scores remain exact."""
    exertion = PerceivedExertion(score)

    assert exertion.score is score
    assert str(exertion) == str(score)


@pytest.mark.parametrize("score", [0, -1, 11])
def test_perceived_exertion_rejects_out_of_range_scores(score: int) -> None:
    """Scores outside the inclusive one-through-ten contract fail."""
    with pytest.raises(InvalidNumericValueError, match="score"):
        PerceivedExertion(score)


@pytest.mark.parametrize("score", [True, 5.0, "5", None])
def test_perceived_exertion_rejects_non_plain_integers(score: object) -> None:
    """Booleans, floats, strings, and unrelated values are not coerced."""
    with pytest.raises(InvalidNumericValueError, match="plain integer"):
        PerceivedExertion(score)  # type: ignore[arg-type]


def test_perceived_exertion_has_value_equality_hashing_and_immutability() -> None:
    """Exertion scores are immutable, hashable value objects."""
    first = PerceivedExertion(7)
    same = PerceivedExertion(7)

    assert first == same
    assert hash(first) == hash(same)
    with pytest.raises(FrozenInstanceError):
        first.score = 8


def test_daily_activity_accepts_all_zero_values() -> None:
    """A reporting day with no recorded activity totals is valid."""
    record = _daily_record()

    assert record.steps == 0
    assert record.distance_kilometers == 0.0
    assert record.active_minutes == 0.0
    assert record.active_calories_kcal == 0.0


def test_daily_activity_preserves_representative_numeric_types() -> None:
    """Permitted integer and floating-point measurements are not coerced."""
    record = _daily_record(
        steps=12_345,
        distance_kilometers=8.75,
        active_minutes=90,
        active_calories_kcal=640.5,
    )

    assert record.steps == 12_345
    assert isinstance(record.steps, int)
    assert record.distance_kilometers == 8.75
    assert isinstance(record.distance_kilometers, float)
    assert record.active_minutes == 90
    assert isinstance(record.active_minutes, int)
    assert record.active_calories_kcal == 640.5


def test_daily_activity_preserves_metadata_and_plain_date() -> None:
    """The validated context and reporting date are retained unchanged."""
    metadata = _metadata()
    activity_date = date(2026, 8, 3)
    record = _daily_record(metadata=metadata, activity_date=activity_date)

    assert record.metadata is metadata
    assert record.activity_date is activity_date


def test_daily_activity_metrics_are_independent_and_uncapped() -> None:
    """No cross-field correspondence or arbitrary active-minute cap is imposed."""
    record = _daily_record(
        steps=0,
        distance_kilometers=5,
        active_minutes=2_000,
        active_calories_kcal=0,
    )

    assert record.steps == 0
    assert record.distance_kilometers == 5
    assert record.active_minutes == 2_000


def test_daily_activity_distance_meters_is_direct_unrounded_conversion() -> None:
    """Kilometers convert directly to the taxonomy-supported meter unit."""
    record = _daily_record(distance_kilometers=1.234567)

    assert record.distance_meters == 1.234567 * 1000
    assert record.distance_meters == record.distance_meters


def test_daily_activity_has_value_equality_hashing_and_immutability() -> None:
    """Daily totals are immutable, hashable domain values."""
    first = _daily_record(steps=10_000, distance_kilometers=7.5)
    same = _daily_record(steps=10_000, distance_kilometers=7.5)

    assert first == same
    assert hash(first) == hash(same)
    with pytest.raises(FrozenInstanceError):
        first.steps = 10_001


def test_daily_activity_rejects_wrong_metadata_type() -> None:
    """Raw mappings are not converted into shared metadata."""
    with pytest.raises(DomainValidationError, match="metadata must be a RecordMetadata"):
        DailyActivityRecord(  # type: ignore[arg-type]
            metadata={"record_id": "activity-1"},
            activity_date=date(2026, 8, 3),
        )


@pytest.mark.parametrize("invalid_date", [datetime(2026, 8, 3, tzinfo=UTC), "2026-08-03"])
def test_daily_activity_rejects_non_plain_dates(invalid_date: object) -> None:
    """Datetimes and strings are rejected rather than converted to dates."""
    with pytest.raises(DomainValidationError, match="activity_date must be a plain date"):
        DailyActivityRecord(  # type: ignore[arg-type]
            metadata=_metadata(),
            activity_date=invalid_date,
        )


@pytest.mark.parametrize("steps", [-1, 1.5, True, "1000"])
def test_daily_activity_rejects_invalid_steps(steps: object) -> None:
    """Steps must be a non-negative plain integer count."""
    with pytest.raises(InvalidNumericValueError, match=r"steps.*non-negative plain integer"):
        _daily_record(steps=steps)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        (field_name, value)
        for field_name in (
            "distance_kilometers",
            "active_minutes",
            "active_calories_kcal",
        )
        for value in (-1, True, float("nan"), float("inf"), float("-inf"))
    ],
)
def test_daily_activity_rejects_invalid_independent_numeric_totals(
    field_name: str,
    value: int | float,
) -> None:
    """Every non-step metric applies shared finite non-negative validation."""
    values = {field_name: value}

    with pytest.raises(InvalidNumericValueError, match=field_name):
        DailyActivityRecord(  # type: ignore[arg-type]
            metadata=_metadata(),
            activity_date=date(2026, 8, 3),
            **values,
        )


def test_workout_accepts_minimum_required_values() -> None:
    """Metadata, a positive period, and a controlled type form a valid workout."""
    record = _workout_record()

    assert record.distance_kilometers is None
    assert record.active_calories_kcal is None
    assert record.perceived_exertion is None
    assert record.average_heart_rate_bpm is None


@pytest.mark.parametrize("workout_type", list(WorkoutType))
def test_workout_accepts_every_controlled_type(workout_type: WorkoutType) -> None:
    """Every vendor-neutral workout type is accepted without classification."""
    assert _workout_record(workout_type=workout_type).workout_type is workout_type


def test_workout_accepts_each_optional_measurement() -> None:
    """Optional measurements may be supplied independently."""
    assert _workout_record(distance_kilometers=0).distance_kilometers == 0
    assert _workout_record(active_calories_kcal=0).active_calories_kcal == 0
    exertion = PerceivedExertion(6)
    assert _workout_record(perceived_exertion=exertion).perceived_exertion is exertion
    assert _workout_record(average_heart_rate_bpm=72.5).average_heart_rate_bpm == 72.5


def test_workout_accepts_all_optional_measurements_without_upper_thresholds() -> None:
    """Recorded context is preserved without arbitrary maxima or interpretation."""
    exertion = PerceivedExertion(10)
    record = _workout_record(
        distance_kilometers=42.195,
        active_calories_kcal=2_500,
        perceived_exertion=exertion,
        average_heart_rate_bpm=1_000,
    )

    assert record.distance_kilometers == 42.195
    assert record.active_calories_kcal == 2_500
    assert record.perceived_exertion is exertion
    assert record.average_heart_rate_bpm == 1_000


def test_workout_preserves_metadata_and_period() -> None:
    """Validated shared objects are retained without reconstruction."""
    metadata = _metadata()
    period = _period()
    record = _workout_record(metadata=metadata, period=period)

    assert record.metadata is metadata
    assert record.period is period
    assert record.metadata.notes == "Outdoor session"


def test_workout_handles_utc_cross_midnight_period() -> None:
    """A completed UTC workout may cross a local calendar boundary."""
    start = datetime(2026, 8, 3, 23, 30, tzinfo=UTC)
    record = _workout_record(period=_period(90, start=start))

    assert record.period.end.date() == date(2026, 8, 4)
    assert record.duration_minutes == 90.0


@pytest.mark.parametrize("offset_hours", [5.5, -4])
def test_workout_handles_positive_and_negative_fixed_offsets(offset_hours: float) -> None:
    """Fixed-offset periods preserve their supplied timezone context."""
    fixed_timezone = timezone(timedelta(hours=offset_hours))
    start = datetime(2026, 8, 3, 6, tzinfo=fixed_timezone)
    period = _period(75, start=start)
    record = _workout_record(period=period)

    assert record.period.start is start
    assert record.duration_minutes == 75.0


def test_workout_handles_mixed_offsets_by_absolute_elapsed_time() -> None:
    """Different timestamp offsets produce the correct elapsed duration."""
    start = datetime(2026, 8, 3, 10, tzinfo=timezone(timedelta(hours=2)))
    end = datetime(2026, 8, 3, 10, 30, tzinfo=timezone(timedelta(hours=-3)))
    period = TimeRange(start, end)
    record = _workout_record(period=period)

    assert record.duration_minutes == 330.0


def test_workout_has_value_equality_hashing_and_immutability() -> None:
    """Completed workouts are immutable, hashable domain values."""
    first = _workout_record(distance_kilometers=5, perceived_exertion=PerceivedExertion(7))
    same = _workout_record(distance_kilometers=5, perceived_exertion=PerceivedExertion(7))

    assert first == same
    assert hash(first) == hash(same)
    with pytest.raises(FrozenInstanceError):
        first.workout_type = WorkoutType.WALKING


def test_workout_rejects_wrong_metadata_type() -> None:
    """Raw mappings are not converted into metadata."""
    with pytest.raises(DomainValidationError, match="metadata must be a RecordMetadata"):
        WorkoutRecord(  # type: ignore[arg-type]
            metadata={"record_id": "workout-1"},
            period=_period(),
            workout_type=WorkoutType.RUNNING,
        )


def test_workout_rejects_wrong_period_type() -> None:
    """Raw duration values are not converted into TimeRange objects."""
    with pytest.raises(DomainValidationError, match="period must be a TimeRange"):
        WorkoutRecord(  # type: ignore[arg-type]
            metadata=_metadata(),
            period=60,
            workout_type=WorkoutType.RUNNING,
        )


def test_workout_rejects_zero_duration_period() -> None:
    """A completed workout must span positive elapsed time."""
    timestamp = datetime(2026, 8, 3, 6, tzinfo=UTC)

    with pytest.raises(InvalidTimeRangeError, match="duration greater than zero"):
        _workout_record(period=TimeRange(timestamp, timestamp))


@pytest.mark.parametrize("workout_type", ["running", DataSource.MANUAL])
def test_workout_rejects_invalid_workout_type(workout_type: object) -> None:
    """Raw strings and unrelated enums are not converted into WorkoutType."""
    with pytest.raises(DomainValidationError, match="workout_type must be a WorkoutType"):
        _workout_record(workout_type=workout_type)  # type: ignore[arg-type]


@pytest.mark.parametrize("field_name", ["distance_kilometers", "active_calories_kcal"])
@pytest.mark.parametrize("value", [-1, True, float("nan"), float("inf"), float("-inf")])
def test_workout_rejects_invalid_optional_non_negative_measurements(
    field_name: str,
    value: int | float,
) -> None:
    """Optional distance and energy apply shared finite non-negative validation."""
    values = {field_name: value}

    with pytest.raises(InvalidNumericValueError, match=field_name):
        WorkoutRecord(  # type: ignore[arg-type]
            metadata=_metadata(),
            period=_period(),
            workout_type=WorkoutType.RUNNING,
            **values,
        )


@pytest.mark.parametrize("value", [5, "5", DataSource.MANUAL])
def test_workout_rejects_invalid_perceived_exertion_object(value: object) -> None:
    """Callers must construct the exertion value object explicitly."""
    with pytest.raises(
        DomainValidationError, match="perceived_exertion must be a PerceivedExertion"
    ):
        _workout_record(perceived_exertion=value)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "value",
    [0, -1, True, float("nan"), float("inf"), float("-inf")],
)
def test_workout_rejects_invalid_average_heart_rate(value: int | float) -> None:
    """Average heart rate must be finite, positive, and non-boolean."""
    with pytest.raises(InvalidNumericValueError, match="average_heart_rate_bpm"):
        _workout_record(average_heart_rate_bpm=value)


def test_workout_derived_duration_and_speed_are_unrounded_and_stable() -> None:
    """Duration and neutral average speed use direct deterministic arithmetic."""
    record = _workout_record(period=_period(90.5), distance_kilometers=10.25)
    expected_speed = 10.25 / (90.5 / 60)

    assert record.duration_minutes == 90.5
    assert record.duration_hours == 90.5 / 60
    assert record.average_speed_kmh == expected_speed
    assert record.average_speed_kmh == record.average_speed_kmh


def test_workout_average_speed_is_none_without_distance() -> None:
    """Missing distance remains unknown rather than being estimated."""
    assert _workout_record().average_speed_kmh is None


def test_workout_average_speed_is_zero_for_recorded_zero_distance() -> None:
    """A recorded zero distance produces a neutral zero speed."""
    assert _workout_record(distance_kilometers=0).average_speed_kmh == 0.0


def test_domain_package_exposes_activity_domain_api() -> None:
    """The authoritative export list preserves foundations, sleep, and activity."""
    expected_exports = {
        "ConfidenceLevel": ConfidenceLevel,
        "DailyActivityRecord": DailyActivityRecord,
        "DataSource": DataSource,
        "DomainValidationError": DomainValidationError,
        "InsightSeverity": InsightSeverity,
        "InvalidIdentifierError": InvalidIdentifierError,
        "InvalidNumericValueError": InvalidNumericValueError,
        "InvalidTimeRangeError": InvalidTimeRangeError,
        "InvalidTimestampError": InvalidTimestampError,
        "MeasurementUnit": MeasurementUnit,
        "MetricIdentifier": MetricIdentifier,
        "PerceivedExertion": PerceivedExertion,
        "RecordId": RecordId,
        "RecordMetadata": RecordMetadata,
        "SleepQuality": SleepQuality,
        "SleepRecord": SleepRecord,
        "SleepStageDurations": SleepStageDurations,
        "TimeRange": TimeRange,
        "WellnessCategory": WellnessCategory,
        "WorkoutRecord": WorkoutRecord,
        "WorkoutType": WorkoutType,
    }

    assert set(expected_exports) <= set(domain.__all__)
    for name, expected_object in expected_exports.items():
        assert getattr(domain, name) is expected_object
