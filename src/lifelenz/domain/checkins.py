"""Immutable domain types for subjective wellness check-ins."""

from dataclasses import dataclass
from enum import StrEnum, unique

from lifelenz.domain.exceptions import DomainValidationError, InvalidNumericValueError
from lifelenz.domain.primitives import RecordMetadata
from lifelenz.domain.validation import require_in_range


@dataclass(frozen=True, slots=True)
class SubjectiveScore:
    """A user-reported plain integer score from 1 through 10, inclusive.

    The endpoints are user-defined reporting-scale boundaries without health
    meaning. Scores are not medical assessments or inherently comparable
    between users.

    Raises:
        InvalidNumericValueError: If ``value`` is not a plain integer in range.
    """

    value: int

    def __post_init__(self) -> None:
        """Validate the score without conversion or interpretation."""
        if type(self.value) is not int:
            raise InvalidNumericValueError(
                f"value must be a plain integer from 1 through 10; got {self.value!r}"
            )
        require_in_range(self.value, 1, 10, field_name="value")

    def __str__(self) -> str:
        """Return the exact numeric score as text."""
        return str(self.value)


@unique
class MoodCategory(StrEnum):
    """Optional neutral user-selected descriptions of reported mood."""

    VERY_LOW = "very_low"
    LOW = "low"
    NEUTRAL = "neutral"
    HIGH = "high"
    VERY_HIGH = "very_high"


@unique
class CheckInTag(StrEnum):
    """Neutral user-selected context tags without diagnostic meaning."""

    RESTED = "rested"
    TIRED = "tired"
    FOCUSED = "focused"
    DISTRACTED = "distracted"
    CALM = "calm"
    TENSE = "tense"
    MOTIVATED = "motivated"
    UNMOTIVATED = "unmotivated"
    SOCIAL = "social"
    SOLITARY = "solitary"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class SubjectiveWellnessCheckIn:
    """One timestamped, non-diagnostic subjective wellness check-in.

    ``metadata.recorded_at`` supplies the timestamp and ``metadata.notes``
    carries optional free-form notes. Mood, energy, and stress are required;
    motivation and a user-selected mood category are optional. Tags are an
    immutable ordered tuple and duplicates are rejected. Higher values reflect
    only future product-interface conventions: potentially more positive mood,
    greater energy, greater stress, or optional motivation as self-reported.
    This record calculates no trends, baselines, correlations, recovery,
    recommendations, or user-to-user comparisons.

    Raises:
        DomainValidationError: If metadata, a score object, category, or tags
            violate the check-in contract.
    """

    metadata: RecordMetadata
    mood_score: SubjectiveScore
    energy_score: SubjectiveScore
    stress_score: SubjectiveScore
    motivation_score: SubjectiveScore | None = None
    mood_category: MoodCategory | None = None
    tags: tuple[CheckInTag, ...] = ()

    def __post_init__(self) -> None:
        """Validate supplied objects and ordered tags without coercion."""
        if not isinstance(self.metadata, RecordMetadata):
            raise DomainValidationError(f"metadata must be a RecordMetadata; got {self.metadata!r}")

        for field_name in ("mood_score", "energy_score", "stress_score"):
            score = getattr(self, field_name)
            if not isinstance(score, SubjectiveScore):
                raise DomainValidationError(
                    f"{field_name} must be a SubjectiveScore; got {score!r}"
                )

        if self.motivation_score is not None and not isinstance(
            self.motivation_score,
            SubjectiveScore,
        ):
            raise DomainValidationError(
                f"motivation_score must be a SubjectiveScore or None; got {self.motivation_score!r}"
            )
        if self.mood_category is not None and not isinstance(
            self.mood_category,
            MoodCategory,
        ):
            raise DomainValidationError(
                f"mood_category must be a MoodCategory or None; got {self.mood_category!r}"
            )
        if type(self.tags) is not tuple:
            raise DomainValidationError(
                f"tags must be a tuple of CheckInTag values; got {self.tags!r}"
            )
        if any(not isinstance(tag, CheckInTag) for tag in self.tags):
            raise DomainValidationError(f"every tag must be a CheckInTag; got {self.tags!r}")
        if len(set(self.tags)) != len(self.tags):
            raise DomainValidationError(f"tags must not contain duplicates; got {self.tags!r}")

    @property
    def has_motivation_score(self) -> bool:
        """Return whether motivation was explicitly reported."""
        return self.motivation_score is not None

    @property
    def tag_count(self) -> int:
        """Return the number of unique ordered context tags."""
        return len(self.tags)
