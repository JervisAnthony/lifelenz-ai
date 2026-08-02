"""Tests for completed sleep-session domain types."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone

import pytest

from lifelenz import domain
from lifelenz.domain import (
    ConfidenceLevel,
    DataSource,
    DomainValidationError,
    InsightSeverity,
    InvalidIdentifierError,
    InvalidNumericValueError,
    InvalidTimeRangeError,
    InvalidTimestampError,
    MeasurementUnit,
    MetricIdentifier,
    RecordId,
    RecordMetadata,
    SleepQuality,
    SleepRecord,
    SleepStageDurations,
    TimeRange,
    WellnessCategory,
)


def _metadata() -> RecordMetadata:
    """Return valid shared metadata for a sleep record."""
    return RecordMetadata(
        record_id=RecordId("sleep-record-1"),
        recorded_at=datetime(2026, 8, 3, 8, tzinfo=UTC),
        source=DataSource.MANUAL,
    )


def _period(
    minutes: int | float = 480,
    *,
    start: datetime | None = None,
) -> TimeRange:
    """Return a valid time-in-bed period with the requested duration."""
    period_start = start or datetime(2026, 8, 2, 22, tzinfo=UTC)
    return TimeRange(period_start, period_start + timedelta(minutes=minutes))


def _record(
    *,
    metadata: RecordMetadata | None = None,
    period: TimeRange | None = None,
    sleep_minutes: int | float = 420,
    awake_minutes: int | float = 60,
    quality: SleepQuality | None = None,
    stages: SleepStageDurations | None = None,
    interruption_count: int | None = None,
) -> SleepRecord:
    """Build a sleep record while keeping individual test setup focused."""
    return SleepRecord(
        metadata=metadata or _metadata(),
        period=period or _period(),
        sleep_minutes=sleep_minutes,
        awake_minutes=awake_minutes,
        quality=quality,
        stages=stages,
        interruption_count=interruption_count,
    )


def test_sleep_quality_has_exact_unique_stable_members() -> None:
    """Subjective quality values expose the intended serialized vocabulary."""
    expected = {
        "VERY_POOR": "very_poor",
        "POOR": "poor",
        "FAIR": "fair",
        "GOOD": "good",
        "VERY_GOOD": "very_good",
    }

    assert {member.name: member.value for member in SleepQuality} == expected
    assert len({member.value for member in SleepQuality}) == len(expected)
    assert all(str(member) == member.value for member in SleepQuality)


def test_sleep_stages_allow_empty_default_set() -> None:
    """Omitted stage information remains a valid all-zero partial set."""
    stages = SleepStageDurations()

    assert stages == SleepStageDurations(0.0, 0.0, 0.0, 0.0)
    assert stages.total_minutes == 0.0


def test_sleep_stages_preserve_integer_and_float_values() -> None:
    """Valid stage inputs are retained without numeric coercion."""
    stages = SleepStageDurations(
        awake_minutes=20,
        light_minutes=180.5,
        deep_minutes=90,
        rem_minutes=70.25,
    )

    assert stages.awake_minutes == 20
    assert isinstance(stages.awake_minutes, int)
    assert stages.light_minutes == 180.5
    assert isinstance(stages.light_minutes, float)
    assert stages.total_minutes == 360.75


@pytest.mark.parametrize(
    "field_name",
    ["awake_minutes", "light_minutes", "deep_minutes", "rem_minutes"],
)
def test_sleep_stages_reject_negative_values(field_name: str) -> None:
    """Every stage field applies the shared non-negative contract."""
    values = {field_name: -0.1}

    with pytest.raises(InvalidNumericValueError, match=rf"{field_name}.*non-negative"):
        SleepStageDurations(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [True, float("inf"), float("-inf"), float("nan")])
def test_sleep_stages_reject_invalid_numeric_values(value: bool | float) -> None:
    """Booleans and non-finite stage totals cannot enter the domain."""
    with pytest.raises(InvalidNumericValueError, match="awake_minutes"):
        SleepStageDurations(awake_minutes=value)


def test_sleep_stages_have_value_equality_hashing_and_immutability() -> None:
    """Stage totals are immutable, hashable value objects."""
    first = SleepStageDurations(10, 100, 50, 40)
    same = SleepStageDurations(10, 100, 50, 40)

    assert first == same
    assert hash(first) == hash(same)
    with pytest.raises(FrozenInstanceError):
        first.deep_minutes = 60


def test_sleep_record_accepts_minimum_required_values() -> None:
    """Metadata, period, actual sleep, and awake time form a valid record."""
    record = _record()

    assert record.quality is None
    assert record.stages is None
    assert record.interruption_count is None


@pytest.mark.parametrize("quality", list(SleepQuality))
def test_sleep_record_accepts_every_sleep_quality(quality: SleepQuality) -> None:
    """Every controlled subjective rating is valid without interpretation."""
    assert _record(quality=quality).quality is quality


@pytest.mark.parametrize("interruption_count", [None, 0, 3])
def test_sleep_record_accepts_known_and_unknown_interruption_counts(
    interruption_count: int | None,
) -> None:
    """Unknown, zero, and positive interruption counts are valid."""
    assert _record(interruption_count=interruption_count).interruption_count == interruption_count


def test_sleep_record_preserves_metadata_period_and_optional_stages() -> None:
    """Validated parent objects are retained without reconstruction."""
    metadata = _metadata()
    period = _period()
    stages = SleepStageDurations(30, 180, 120, 90)
    record = _record(metadata=metadata, period=period, stages=stages)

    assert record.metadata is metadata
    assert record.period is period
    assert record.stages is stages


def test_sleep_record_accepts_partial_stage_data() -> None:
    """Stage totals need not account for all parent sleep and awake minutes."""
    stages = SleepStageDurations(awake_minutes=5, deep_minutes=60)

    assert _record(stages=stages).stages is stages


def test_sleep_record_accepts_decimal_minutes_and_zero_awake_time() -> None:
    """Decimal-minute precision and no awake time are both valid."""
    sleep_minutes = 419.75
    record = _record(sleep_minutes=sleep_minutes, awake_minutes=0)

    assert record.sleep_minutes is sleep_minutes
    assert record.awake_minutes == 0


def test_sleep_record_allows_sleep_to_equal_complete_period() -> None:
    """A full-period sleep duration produces a valid 100 percent efficiency."""
    record = _record(sleep_minutes=480, awake_minutes=0)

    assert record.sleep_efficiency_percent == 100.0


def test_sleep_record_accepts_exactly_accounted_period() -> None:
    """Sleep and awake minutes may exactly equal time in bed."""
    record = _record(sleep_minutes=420, awake_minutes=60)

    assert record.sleep_minutes + record.awake_minutes == record.time_in_bed_minutes


def test_sleep_record_allows_unclassified_time() -> None:
    """Parent durations may total less than the complete time in bed."""
    record = _record(sleep_minutes=400, awake_minutes=40)

    assert record.sleep_minutes + record.awake_minutes < record.time_in_bed_minutes


def test_sleep_record_accepts_tiny_floating_point_total_difference() -> None:
    """Representation noise does not invalidate an equivalent duration total."""
    record = _record(period=_period(0.3), sleep_minutes=0.1, awake_minutes=0.2)

    assert record.sleep_minutes + record.awake_minutes > record.time_in_bed_minutes


def test_sleep_record_rejects_material_combined_duration_overrun() -> None:
    """The private tolerance does not admit a meaningful excess."""
    with pytest.raises(InvalidNumericValueError, match=r"sleep_minutes plus awake_minutes.*time"):
        _record(period=_period(0.3), sleep_minutes=0.100001, awake_minutes=0.2)


def test_sleep_record_rejects_zero_duration_period() -> None:
    """A completed sleep session must span positive elapsed time."""
    timestamp = datetime(2026, 8, 2, 22, tzinfo=UTC)

    with pytest.raises(InvalidTimeRangeError, match="duration greater than zero"):
        _record(period=TimeRange(timestamp, timestamp), sleep_minutes=1, awake_minutes=0)


def test_sleep_record_rejects_wrong_metadata_type() -> None:
    """Raw mappings are not converted into metadata."""
    with pytest.raises(DomainValidationError, match="metadata must be a RecordMetadata"):
        SleepRecord(  # type: ignore[arg-type]
            metadata={"record_id": "sleep-1"},
            period=_period(),
            sleep_minutes=420,
            awake_minutes=60,
        )


def test_sleep_record_rejects_wrong_period_type() -> None:
    """Raw values are not converted into time ranges."""
    with pytest.raises(DomainValidationError, match="period must be a TimeRange"):
        SleepRecord(  # type: ignore[arg-type]
            metadata=_metadata(),
            period="eight hours",
            sleep_minutes=420,
            awake_minutes=60,
        )


def test_sleep_record_handles_cross_midnight_period() -> None:
    """A local-midnight boundary does not change elapsed-time calculation."""
    period = _period(450, start=datetime(2026, 8, 2, 22, 30, tzinfo=UTC))
    record = _record(period=period, sleep_minutes=400, awake_minutes=50)

    assert record.period.end.date() == datetime(2026, 8, 3, tzinfo=UTC).date()
    assert record.time_in_bed_minutes == 450.0


def test_sleep_record_handles_different_positive_and_negative_offsets() -> None:
    """Time in bed uses equivalent absolute instants across fixed offsets."""
    start = datetime(2026, 8, 2, 22, tzinfo=timezone(timedelta(hours=2)))
    end = datetime(2026, 8, 3, 1, tzinfo=timezone(timedelta(hours=-5)))
    period = TimeRange(start, end)
    record = _record(period=period, sleep_minutes=540, awake_minutes=60)

    assert record.period.start is start
    assert record.period.end is end
    assert record.time_in_bed_minutes == 600.0


@pytest.mark.parametrize("value", [0, -1, True, float("inf"), float("-inf"), float("nan")])
def test_sleep_record_rejects_invalid_sleep_minutes(value: int | float) -> None:
    """Actual sleep must be finite, non-boolean, and strictly positive."""
    with pytest.raises(InvalidNumericValueError, match="sleep_minutes"):
        _record(sleep_minutes=value)


def test_sleep_record_rejects_sleep_above_time_in_bed() -> None:
    """Actual sleep cannot exceed the complete session period."""
    with pytest.raises(InvalidNumericValueError, match=r"sleep_minutes cannot exceed time in bed"):
        _record(sleep_minutes=480.01, awake_minutes=0)


@pytest.mark.parametrize("value", [-1, True, float("inf"), float("-inf"), float("nan")])
def test_sleep_record_rejects_invalid_awake_minutes(value: int | float) -> None:
    """Awake time must be finite, non-boolean, and non-negative."""
    with pytest.raises(InvalidNumericValueError, match="awake_minutes"):
        _record(awake_minutes=value)


def test_sleep_record_rejects_awake_time_above_time_in_bed() -> None:
    """Awake time cannot individually exceed the session period."""
    with pytest.raises(InvalidNumericValueError, match=r"awake_minutes cannot exceed time in bed"):
        _record(sleep_minutes=1, awake_minutes=480.01)


def test_sleep_stages_may_exactly_equal_parent_sleep_duration() -> None:
    """Light, deep, and REM may completely account for actual sleep."""
    stages = SleepStageDurations(
        awake_minutes=60, light_minutes=210, deep_minutes=120, rem_minutes=90
    )

    assert _record(stages=stages).stages is stages


def test_sleep_stages_accept_tiny_floating_point_sleep_difference() -> None:
    """Equivalent staged-sleep arithmetic is accepted within tolerance."""
    stages = SleepStageDurations(light_minutes=0.1, deep_minutes=0.2)

    assert (
        _record(period=_period(1), sleep_minutes=0.3, awake_minutes=0, stages=stages).stages
        is stages
    )


def test_sleep_record_rejects_staged_sleep_above_sleep_minutes() -> None:
    """Asleep stages cannot materially exceed actual sleep."""
    stages = SleepStageDurations(light_minutes=200, deep_minutes=150, rem_minutes=71)

    with pytest.raises(InvalidNumericValueError, match=r"sleep stage sleep minutes.*sleep_minutes"):
        _record(stages=stages)


def test_sleep_record_rejects_staged_awake_above_awake_minutes() -> None:
    """Staged awake time cannot exceed the parent awake duration."""
    stages = SleepStageDurations(awake_minutes=61, light_minutes=200)

    with pytest.raises(InvalidNumericValueError, match=r"stages.awake_minutes.*awake_minutes"):
        _record(stages=stages)


def test_sleep_record_rejects_complete_stage_total_above_time_in_bed() -> None:
    """Complete stage accounting cannot exceed the session period."""
    stages = SleepStageDurations(awake_minutes=30, light_minutes=40)

    with pytest.raises(InvalidNumericValueError, match=r"total staged minutes.*time in bed"):
        _record(period=_period(60), sleep_minutes=40, awake_minutes=30, stages=stages)


def test_sleep_record_rejects_wrong_stage_object_type() -> None:
    """Raw mappings are not converted into stage-duration objects."""
    with pytest.raises(DomainValidationError, match="stages must be SleepStageDurations"):
        SleepRecord(  # type: ignore[arg-type]
            metadata=_metadata(),
            period=_period(),
            sleep_minutes=420,
            awake_minutes=60,
            stages={"deep_minutes": 90},
        )


@pytest.mark.parametrize("value", [-1, 1.5, True, "3"])
def test_sleep_record_rejects_invalid_interruption_count(value: object) -> None:
    """Known interruption counts must be non-negative plain integers."""
    with pytest.raises(InvalidNumericValueError, match=r"interruption_count.*non-negative integer"):
        _record(interruption_count=value)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", ["good", DataSource.MANUAL])
def test_sleep_record_rejects_invalid_quality_type(value: object) -> None:
    """Raw strings and unrelated enums are not converted to SleepQuality."""
    with pytest.raises(DomainValidationError, match="quality must be a SleepQuality"):
        _record(quality=value)  # type: ignore[arg-type]


def test_sleep_record_derived_properties_are_unrounded_and_stable() -> None:
    """Derived display units and efficiency remain deterministic floats."""
    record = _record(period=_period(470), sleep_minutes=400, awake_minutes=35)

    expected_efficiency = 400 / 470 * 100
    assert record.time_in_bed_minutes == 470.0
    assert record.time_in_bed_hours == 470 / 60
    assert record.sleep_duration_hours == 400 / 60
    assert record.awake_duration_hours == 35 / 60
    assert record.sleep_efficiency_percent == expected_efficiency
    assert record.sleep_efficiency_percent == record.sleep_efficiency_percent
    assert 0.0 <= record.sleep_efficiency_percent <= 100.0


def test_sleep_record_has_value_equality_hashing_and_immutability() -> None:
    """Sleep sessions are immutable, hashable domain values."""
    first = _record(quality=SleepQuality.GOOD, interruption_count=1)
    same = _record(quality=SleepQuality.GOOD, interruption_count=1)

    assert first == same
    assert hash(first) == hash(same)
    with pytest.raises(FrozenInstanceError):
        first.sleep_minutes = 400


def test_domain_package_exposes_complete_sleep_domain_api() -> None:
    """The curated API preserves foundations and adds only public sleep types."""
    expected_exports = {
        "ConfidenceLevel": ConfidenceLevel,
        "DataSource": DataSource,
        "DomainValidationError": DomainValidationError,
        "InsightSeverity": InsightSeverity,
        "InvalidIdentifierError": InvalidIdentifierError,
        "InvalidNumericValueError": InvalidNumericValueError,
        "InvalidTimeRangeError": InvalidTimeRangeError,
        "InvalidTimestampError": InvalidTimestampError,
        "MeasurementUnit": MeasurementUnit,
        "MetricIdentifier": MetricIdentifier,
        "RecordId": RecordId,
        "RecordMetadata": RecordMetadata,
        "SleepQuality": SleepQuality,
        "SleepRecord": SleepRecord,
        "SleepStageDurations": SleepStageDurations,
        "TimeRange": TimeRange,
        "WellnessCategory": WellnessCategory,
    }

    assert domain.__all__ == list(expected_exports)
    for name, expected_object in expected_exports.items():
        assert getattr(domain, name) is expected_object
