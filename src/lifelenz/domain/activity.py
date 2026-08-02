"""Immutable domain types for daily activity and completed workouts."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum, unique

from lifelenz.domain.exceptions import (
    DomainValidationError,
    InvalidNumericValueError,
    InvalidTimeRangeError,
)
from lifelenz.domain.primitives import RecordMetadata, TimeRange
from lifelenz.domain.validation import require_in_range, require_non_negative, require_positive


@unique
class WorkoutType(StrEnum):
    """Vendor-neutral types for completed physical-activity sessions."""

    WALKING = "walking"
    RUNNING = "running"
    CYCLING = "cycling"
    SWIMMING = "swimming"
    STRENGTH_TRAINING = "strength_training"
    YOGA = "yoga"
    HIKING = "hiking"
    ROWING = "rowing"
    ELLIPTICAL = "elliptical"
    SPORT = "sport"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class PerceivedExertion:
    """A subjective integer effort score from 1 through 10, inclusive.

    The score is preserved exactly and carries no training-zone or medical label.

    Raises:
        InvalidNumericValueError: If ``score`` is not a plain integer in range.
    """

    score: int

    def __post_init__(self) -> None:
        """Validate the score without coercion or interpretation."""
        if type(self.score) is not int:
            raise InvalidNumericValueError(
                f"score must be a plain integer from 1 through 10; got {self.score!r}"
            )
        require_in_range(self.score, 1, 10, field_name="score")

    def __str__(self) -> str:
        """Return the exact numeric score as text."""
        return str(self.score)


@dataclass(frozen=True, slots=True)
class DailyActivityRecord:
    """Independent physical-activity totals for one reporting date.

    Distance is stored in kilometers, active duration in minutes, and energy
    in kcal. Metrics are validated independently without inferred relationships
    or population-based classifications.

    Raises:
        DomainValidationError: If metadata or the reporting date is invalid.
        InvalidNumericValueError: If steps or another numeric total is invalid.
    """

    metadata: RecordMetadata
    activity_date: date
    steps: int = 0
    distance_kilometers: int | float = 0.0
    active_minutes: int | float = 0.0
    active_calories_kcal: int | float = 0.0

    def __post_init__(self) -> None:
        """Validate metadata, reporting date, and independent daily totals."""
        if not isinstance(self.metadata, RecordMetadata):
            raise DomainValidationError(f"metadata must be a RecordMetadata; got {self.metadata!r}")
        if type(self.activity_date) is not date:
            raise DomainValidationError(
                f"activity_date must be a plain date; got {self.activity_date!r}"
            )
        if type(self.steps) is not int or self.steps < 0:
            raise InvalidNumericValueError(
                f"steps must be a non-negative plain integer; got {self.steps!r}"
            )

        require_non_negative(self.distance_kilometers, field_name="distance_kilometers")
        require_non_negative(self.active_minutes, field_name="active_minutes")
        require_non_negative(self.active_calories_kcal, field_name="active_calories_kcal")

    @property
    def distance_meters(self) -> int | float:
        """Return recorded distance converted directly to meters."""
        return self.distance_kilometers * 1000


@dataclass(frozen=True, slots=True)
class WorkoutRecord:
    """A completed workout with optional neutral recorded measurements.

    ``period`` is the start-inclusive, end-exclusive completed session. Distance
    is in kilometers, active energy is in kcal, and average heart rate is in
    beats per minute without zones, thresholds, or health interpretation.

    Raises:
        DomainValidationError: If a supplied object or controlled type is invalid.
        InvalidTimeRangeError: If the workout period has zero duration.
        InvalidNumericValueError: If an optional numeric measurement is invalid.
    """

    metadata: RecordMetadata
    period: TimeRange
    workout_type: WorkoutType
    distance_kilometers: int | float | None = None
    active_calories_kcal: int | float | None = None
    perceived_exertion: PerceivedExertion | None = None
    average_heart_rate_bpm: int | float | None = None

    def __post_init__(self) -> None:
        """Validate the completed period, type, and optional measurements."""
        if not isinstance(self.metadata, RecordMetadata):
            raise DomainValidationError(f"metadata must be a RecordMetadata; got {self.metadata!r}")
        if not isinstance(self.period, TimeRange):
            raise DomainValidationError(f"period must be a TimeRange; got {self.period!r}")
        if self.period.duration.total_seconds() == 0:
            raise InvalidTimeRangeError("workout period must have a duration greater than zero")
        if not isinstance(self.workout_type, WorkoutType):
            raise DomainValidationError(
                f"workout_type must be a WorkoutType; got {self.workout_type!r}"
            )

        if self.distance_kilometers is not None:
            require_non_negative(
                self.distance_kilometers,
                field_name="distance_kilometers",
            )
        if self.active_calories_kcal is not None:
            require_non_negative(
                self.active_calories_kcal,
                field_name="active_calories_kcal",
            )
        if self.perceived_exertion is not None and not isinstance(
            self.perceived_exertion,
            PerceivedExertion,
        ):
            raise DomainValidationError(
                "perceived_exertion must be a PerceivedExertion or None; "
                f"got {self.perceived_exertion!r}"
            )
        if self.average_heart_rate_bpm is not None:
            require_positive(
                self.average_heart_rate_bpm,
                field_name="average_heart_rate_bpm",
            )

    @property
    def duration_minutes(self) -> float:
        """Return completed workout duration in minutes."""
        return self.period.duration_minutes

    @property
    def duration_hours(self) -> float:
        """Return completed workout duration in hours without rounding."""
        return self.duration_minutes / 60

    @property
    def average_speed_kmh(self) -> float | None:
        """Return direct average speed, or ``None`` when distance is absent."""
        if self.distance_kilometers is None:
            return None
        return self.distance_kilometers / self.duration_hours
