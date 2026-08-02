"""Immutable primitives shared by future LifeLenz wellness records."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Self
from uuid import uuid4

from lifelenz.domain.exceptions import (
    DomainValidationError,
    InvalidIdentifierError,
    InvalidTimeRangeError,
)
from lifelenz.domain.taxonomy import DataSource
from lifelenz.domain.validation import require_timezone_aware_datetime


@dataclass(frozen=True, slots=True)
class RecordId:
    """An opaque record identifier with stable value equality and hashing.

    Supplied values must be non-empty strings without whitespace anywhere in
    the value. Values are validated but never normalized or generated implicitly.

    Raises:
        InvalidIdentifierError: If ``value`` is not a valid supplied identifier.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate the supplied identifier without changing it."""
        if not isinstance(self.value, str):
            raise InvalidIdentifierError(f"record identifier must be a string; got {self.value!r}")
        if not self.value:
            raise InvalidIdentifierError("record identifier must not be empty")
        if any(character.isspace() for character in self.value):
            raise InvalidIdentifierError(
                f"record identifier must not contain whitespace; got {self.value!r}"
            )

    @classmethod
    def generate(cls) -> Self:
        """Return a new identifier backed by a standard UUID4 value."""
        return cls(str(uuid4()))

    def __str__(self) -> str:
        """Return the identifier's exact stored value."""
        return self.value


@dataclass(frozen=True, slots=True)
class TimeRange:
    """A start-inclusive, end-exclusive range between aware timestamps.

    Zero-duration ranges are permitted. Original datetime objects and their
    timezones are preserved without conversion.

    Raises:
        InvalidTimestampError: If either bound is not timezone-aware.
        InvalidTimeRangeError: If ``end`` occurs before ``start``.
    """

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        """Validate timezone awareness and absolute bound ordering."""
        require_timezone_aware_datetime(self.start, field_name="start")
        require_timezone_aware_datetime(self.end, field_name="end")
        if self.end.astimezone(UTC) < self.start.astimezone(UTC):
            raise InvalidTimeRangeError(
                f"end must not occur before start; got start={self.start!r}, end={self.end!r}"
            )

    @property
    def duration(self) -> timedelta:
        """Return elapsed time between the range bounds."""
        return self.end.astimezone(UTC) - self.start.astimezone(UTC)

    @property
    def duration_minutes(self) -> float:
        """Return elapsed duration as a floating-point number of minutes."""
        return self.duration.total_seconds() / 60


@dataclass(frozen=True, slots=True)
class RecordMetadata:
    """Common non-persistence metadata for future wellness records.

    ``recorded_at`` must be timezone-aware and ``source`` must already be a
    ``DataSource``. Notes are trimmed; empty or whitespace-only notes become
    ``None``.

    Raises:
        InvalidIdentifierError: If ``record_id`` is not a ``RecordId``.
        InvalidTimestampError: If ``recorded_at`` is not timezone-aware.
        DomainValidationError: If ``source`` or ``notes`` has an invalid type.
    """

    record_id: RecordId
    recorded_at: datetime
    source: DataSource
    notes: str | None = None

    def __post_init__(self) -> None:
        """Validate metadata and apply the documented notes normalization."""
        if not isinstance(self.record_id, RecordId):
            raise InvalidIdentifierError(f"record_id must be a RecordId; got {self.record_id!r}")
        require_timezone_aware_datetime(self.recorded_at, field_name="recorded_at")
        if not isinstance(self.source, DataSource):
            raise DomainValidationError(f"source must be a DataSource; got {self.source!r}")
        if self.notes is not None and not isinstance(self.notes, str):
            raise DomainValidationError(f"notes must be a string or None; got {self.notes!r}")

        normalized_notes = self.notes.strip() if self.notes is not None else None
        object.__setattr__(self, "notes", normalized_notes or None)
