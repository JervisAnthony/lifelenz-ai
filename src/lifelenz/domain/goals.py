"""Immutable domain types for user-defined wellness goals."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum, unique
from typing import Self
from uuid import UUID, uuid4

from lifelenz.domain.exceptions import DomainValidationError, InvalidIdentifierError
from lifelenz.domain.profile import ProfileId
from lifelenz.domain.taxonomy import (
    DEFAULT_UNIT_BY_METRIC,
    MeasurementUnit,
    MetricIdentifier,
)
from lifelenz.domain.validation import require_non_negative


@dataclass(frozen=True, slots=True)
class GoalId:
    """A goal-specific identifier using preserved canonical UUID text.

    Raises:
        InvalidIdentifierError: If ``value`` is not canonical UUID text.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate canonical UUID text without changing the supplied value."""
        if not isinstance(self.value, str):
            raise InvalidIdentifierError(f"goal identifier must be a string; got {self.value!r}")
        if not self.value:
            raise InvalidIdentifierError("goal identifier must not be empty")
        if any(character.isspace() for character in self.value):
            raise InvalidIdentifierError(
                f"goal identifier must not contain whitespace; got {self.value!r}"
            )

        try:
            parsed_value = UUID(self.value)
        except (ValueError, AttributeError) as error:
            raise InvalidIdentifierError(
                f"goal identifier must be a valid UUID; got {self.value!r}"
            ) from error
        if self.value.lower() != str(parsed_value):
            raise InvalidIdentifierError(
                f"goal identifier must use canonical UUID text; got {self.value!r}"
            )

    @classmethod
    def generate(cls) -> Self:
        """Return a new goal identifier backed by a standard UUID4 value."""
        return cls(str(uuid4()))

    def __str__(self) -> str:
        """Return the exact stored identifier text."""
        return self.value


@unique
class GoalDirection(StrEnum):
    """Neutral user-selected intent relative to a canonical metric target."""

    AT_LEAST = "at_least"
    AT_MOST = "at_most"
    EXACTLY = "exactly"
    INCREASE = "increase"
    DECREASE = "decrease"
    MAINTAIN = "maintain"


@unique
class GoalStatus(StrEnum):
    """Explicitly supplied goal lifecycle state without progress calculation."""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class GoalTarget:
    """A finite non-negative target using a metric's canonical taxonomy unit.

    The numeric value is preserved without conversion or rounding. Target
    suitability, health meaning, and recommendations are outside this domain.

    Raises:
        DomainValidationError: If metric or unit is invalid or incompatible.
        InvalidNumericValueError: If ``value`` is not finite and non-negative.
    """

    metric: MetricIdentifier
    value: int | float
    unit: MeasurementUnit

    def __post_init__(self) -> None:
        """Validate controlled types, value, and canonical-unit compatibility."""
        if not isinstance(self.metric, MetricIdentifier):
            raise DomainValidationError(f"metric must be a MetricIdentifier; got {self.metric!r}")
        if not isinstance(self.unit, MeasurementUnit):
            raise DomainValidationError(f"unit must be a MeasurementUnit; got {self.unit!r}")
        require_non_negative(self.value, field_name="value")

        canonical_unit = DEFAULT_UNIT_BY_METRIC[self.metric]
        if self.unit is not canonical_unit:
            raise DomainValidationError(
                f"unit must be {canonical_unit.value!r} for metric {self.metric.value!r}; "
                f"got {self.unit.value!r}"
            )


@dataclass(frozen=True, slots=True)
class WellnessGoal:
    """One immutable user-defined goal associated with a profile identifier.

    The target uses canonical taxonomy units. Direction, status, and optional
    dates are supplied explicitly and never inferred. Optional title and
    description trim surrounding whitespace. This record calculates no
    progress, achievement, overdue state, recommendation, or medical meaning.

    Raises:
        DomainValidationError: If an identifier, object, enum, date, or text
            field violates the goal contract.
    """

    goal_id: GoalId
    profile_id: ProfileId
    target: GoalTarget
    direction: GoalDirection
    status: GoalStatus = GoalStatus.DRAFT
    start_date: date | None = None
    target_date: date | None = None
    title: str | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        """Validate explicit goal values without coercion or inference."""
        if not isinstance(self.goal_id, GoalId):
            raise DomainValidationError(f"goal_id must be a GoalId; got {self.goal_id!r}")
        if not isinstance(self.profile_id, ProfileId):
            raise DomainValidationError(f"profile_id must be a ProfileId; got {self.profile_id!r}")
        if not isinstance(self.target, GoalTarget):
            raise DomainValidationError(f"target must be a GoalTarget; got {self.target!r}")
        if not isinstance(self.direction, GoalDirection):
            raise DomainValidationError(
                f"direction must be a GoalDirection; got {self.direction!r}"
            )
        if not isinstance(self.status, GoalStatus):
            raise DomainValidationError(f"status must be a GoalStatus; got {self.status!r}")

        if self.start_date is not None and type(self.start_date) is not date:
            raise DomainValidationError(
                f"start_date must be a plain date or None; got {self.start_date!r}"
            )
        if self.target_date is not None and type(self.target_date) is not date:
            raise DomainValidationError(
                f"target_date must be a plain date or None; got {self.target_date!r}"
            )
        if (
            self.start_date is not None
            and self.target_date is not None
            and self.target_date < self.start_date
        ):
            raise DomainValidationError(
                "target_date must not precede start_date; "
                f"got start_date={self.start_date!r}, target_date={self.target_date!r}"
            )

        if self.title is not None and not isinstance(self.title, str):
            raise DomainValidationError(f"title must be a string or None; got {self.title!r}")
        if self.description is not None and not isinstance(self.description, str):
            raise DomainValidationError(
                f"description must be a string or None; got {self.description!r}"
            )
        normalized_title = self.title.strip() if self.title is not None else None
        normalized_description = self.description.strip() if self.description is not None else None
        object.__setattr__(self, "title", normalized_title or None)
        object.__setattr__(self, "description", normalized_description or None)

    @property
    def has_title(self) -> bool:
        """Return whether a non-blank title is present."""
        return self.title is not None

    @property
    def has_description(self) -> bool:
        """Return whether a non-blank description is present."""
        return self.description is not None

    @property
    def has_start_date(self) -> bool:
        """Return whether a user-supplied start date is present."""
        return self.start_date is not None

    @property
    def has_target_date(self) -> bool:
        """Return whether a user-supplied target date is present."""
        return self.target_date is not None

    @property
    def scheduled_span_days(self) -> int | None:
        """Return the inclusive planned date span when both dates are present."""
        if self.start_date is None or self.target_date is None:
            return None
        return (self.target_date - self.start_date).days + 1

    @property
    def is_active(self) -> bool:
        """Return whether the explicitly supplied status is active."""
        return self.status is GoalStatus.ACTIVE

    @property
    def is_terminal(self) -> bool:
        """Return whether status is explicitly completed or cancelled."""
        return self.status in (GoalStatus.COMPLETED, GoalStatus.CANCELLED)
