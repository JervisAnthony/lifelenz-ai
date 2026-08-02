"""Tests for immutable shared LifeLenz domain primitives."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

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
    TimeRange,
    WellnessCategory,
)


@pytest.mark.parametrize("value", ["record-123", "record_123", "external:123"])
def test_record_id_preserves_valid_supplied_value(value: str) -> None:
    """Valid opaque identifiers, including punctuation, remain unchanged."""
    record_id = RecordId(value)

    assert record_id.value == value
    assert str(record_id) == value
    assert repr(record_id) == f"RecordId(value={value!r})"


def test_record_id_rejects_empty_value() -> None:
    """An identifier must contain at least one character."""
    with pytest.raises(InvalidIdentifierError, match="must not be empty"):
        RecordId("")


@pytest.mark.parametrize(
    "value",
    [
        " ",
        "record 123",
        "record\t123",
        "record\n123",
        " record-123",
        "record-123 ",
        "record\u00a0123",
    ],
    ids=[
        "whitespace-only",
        "internal-space",
        "internal-tab",
        "internal-newline",
        "leading-space",
        "trailing-space",
        "unicode-non-breaking-space",
    ],
)
def test_record_id_rejects_whitespace_anywhere(value: str) -> None:
    """ASCII and Unicode whitespace are rejected without normalization."""
    with pytest.raises(InvalidIdentifierError, match="must not contain whitespace"):
        RecordId(value)


def test_record_id_rejects_non_string_value() -> None:
    """Runtime validation protects the identifier boundary."""
    with pytest.raises(InvalidIdentifierError, match="must be a string"):
        RecordId(42)  # type: ignore[arg-type]


def test_record_id_has_value_equality_hashing_and_immutability() -> None:
    """Identifiers behave as immutable values suitable for mapping keys."""
    first = RecordId("record-123")
    same = RecordId("record-123")
    different = RecordId("record-456")

    assert first == same
    assert first != different
    assert hash(first) == hash(same)
    assert {first: "value"}[same] == "value"
    with pytest.raises(FrozenInstanceError):
        first.value = "replacement"


def test_generated_record_ids_are_distinct_uuid4_values() -> None:
    """Explicit generation creates practical globally unique UUID4 identifiers."""
    first = RecordId.generate()
    second = RecordId.generate()

    assert first != second
    assert UUID(first.value).version == 4
    assert UUID(second.value).version == 4


def test_time_range_preserves_same_timezone_bounds_and_calculates_duration() -> None:
    """A valid range retains its datetimes and exposes elapsed time."""
    start = datetime(2026, 8, 2, 9, 15, tzinfo=UTC)
    end = datetime(2026, 8, 2, 10, 45, tzinfo=UTC)
    time_range = TimeRange(start=start, end=end)

    assert time_range.start is start
    assert time_range.end is end
    assert time_range.duration == timedelta(minutes=90)
    assert time_range.duration_minutes == 90.0


def test_time_range_compares_different_offsets_by_absolute_instant() -> None:
    """Different local offsets produce the correct elapsed duration."""
    start = datetime(2026, 8, 2, 10, tzinfo=timezone(timedelta(hours=2)))
    end = datetime(2026, 8, 2, 10, tzinfo=UTC)

    assert TimeRange(start=start, end=end).duration == timedelta(hours=2)


def test_time_range_allows_same_instant_with_different_offsets() -> None:
    """Equivalent instants form a permitted zero-duration range."""
    start = datetime(2026, 8, 2, 12, tzinfo=timezone(timedelta(hours=2)))
    end = datetime(2026, 8, 2, 10, tzinfo=UTC)
    time_range = TimeRange(start=start, end=end)

    assert time_range.duration == timedelta(0)
    assert time_range.duration_minutes == 0.0


def test_time_range_allows_identical_bounds() -> None:
    """Identical aware datetime objects form a zero-duration range."""
    timestamp = datetime(2026, 8, 2, 10, tzinfo=UTC)

    assert TimeRange(timestamp, timestamp).duration == timedelta(0)


@pytest.mark.parametrize("naive_field", ["start", "end"])
def test_time_range_rejects_naive_bounds(naive_field: str) -> None:
    """Each time-range boundary independently requires timezone awareness."""
    aware = datetime(2026, 8, 2, 10, tzinfo=UTC)
    naive = datetime(2026, 8, 2, 10)
    start, end = (naive, aware) if naive_field == "start" else (aware, naive)

    with pytest.raises(InvalidTimestampError, match=rf"{naive_field}.*timezone-aware"):
        TimeRange(start=start, end=end)


def test_time_range_rejects_end_that_looks_later_but_is_earlier_instant() -> None:
    """Ordering uses offsets rather than comparing local clock fields."""
    start = datetime(2026, 8, 2, 9, tzinfo=timezone(timedelta(hours=-5)))
    end = datetime(2026, 8, 2, 10, tzinfo=UTC)

    with pytest.raises(InvalidTimeRangeError, match="end must not occur before start"):
        TimeRange(start=start, end=end)


def test_time_range_is_immutable() -> None:
    """Validated range bounds cannot be replaced."""
    timestamp = datetime(2026, 8, 2, 10, tzinfo=UTC)
    time_range = TimeRange(timestamp, timestamp)

    with pytest.raises(FrozenInstanceError):
        time_range.end = timestamp + timedelta(hours=1)


@pytest.mark.parametrize("record_id", [RecordId("supplied-id"), RecordId.generate()])
def test_record_metadata_accepts_supplied_and_generated_identifiers(record_id: RecordId) -> None:
    """Metadata remains independent of how its valid identifier was obtained."""
    recorded_at = datetime(2026, 8, 2, 10, tzinfo=UTC)
    metadata = RecordMetadata(record_id, recorded_at, DataSource.MANUAL)

    assert metadata.record_id is record_id
    assert metadata.recorded_at is recorded_at
    assert metadata.source is DataSource.MANUAL
    assert metadata.notes is None


@pytest.mark.parametrize(
    ("notes", "expected"),
    [
        (None, None),
        ("", None),
        (" \t\n", None),
        ("  user supplied note  ", "user supplied note"),
    ],
)
def test_record_metadata_normalizes_notes(notes: str | None, expected: str | None) -> None:
    """Notes follow the documented trim-and-collapse normalization."""
    metadata = RecordMetadata(
        RecordId("record-1"),
        datetime(2026, 8, 2, 10, tzinfo=UTC),
        DataSource.CSV_IMPORT,
        notes,
    )

    assert metadata.notes == expected


def test_record_metadata_rejects_invalid_identifier_type() -> None:
    """Metadata requires an already validated RecordId value."""
    with pytest.raises(InvalidIdentifierError, match="record_id must be a RecordId"):
        RecordMetadata(  # type: ignore[arg-type]
            "record-1",
            datetime(2026, 8, 2, 10, tzinfo=UTC),
            DataSource.MANUAL,
        )


def test_record_metadata_rejects_naive_timestamp() -> None:
    """Metadata delegates recorded-at validation to the shared helper."""
    with pytest.raises(InvalidTimestampError, match=r"recorded_at.*timezone-aware"):
        RecordMetadata(RecordId("record-1"), datetime(2026, 8, 2, 10), DataSource.MANUAL)


def test_record_metadata_rejects_invalid_source_type() -> None:
    """Raw source strings are not silently coerced to DataSource members."""
    with pytest.raises(DomainValidationError, match="source must be a DataSource"):
        RecordMetadata(  # type: ignore[arg-type]
            RecordId("record-1"),
            datetime(2026, 8, 2, 10, tzinfo=UTC),
            "manual",
        )


def test_record_metadata_rejects_invalid_notes_type() -> None:
    """Notes accept only strings or None."""
    with pytest.raises(DomainValidationError, match="notes must be a string or None"):
        RecordMetadata(  # type: ignore[arg-type]
            RecordId("record-1"),
            datetime(2026, 8, 2, 10, tzinfo=UTC),
            DataSource.MANUAL,
            42,
        )


def test_record_metadata_has_value_equality_hashing_and_immutability() -> None:
    """Normalized metadata is an immutable, hashable value object."""
    recorded_at = datetime(2026, 8, 2, 10, tzinfo=UTC)
    first = RecordMetadata(RecordId("record-1"), recorded_at, DataSource.API_IMPORT, " note ")
    same = RecordMetadata(RecordId("record-1"), recorded_at, DataSource.API_IMPORT, "note")

    assert first == same
    assert hash(first) == hash(same)
    with pytest.raises(FrozenInstanceError):
        first.notes = "replacement"


def test_domain_package_exposes_complete_curated_public_api() -> None:
    """New primitives and exceptions join the existing taxonomy exports."""
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
        "TimeRange": TimeRange,
        "WellnessCategory": WellnessCategory,
    }

    assert domain.__all__ == list(expected_exports)
    for name, expected_object in expected_exports.items():
        assert getattr(domain, name) is expected_object
    assert "require_positive" not in domain.__all__
