"""Immutable domain types for neutral menstrual-cycle tracking."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum, unique

from lifelenz.domain.exceptions import DomainValidationError
from lifelenz.domain.primitives import RecordMetadata


@unique
class MenstrualFlow(StrEnum):
    """Vendor-neutral, user-reported menstrual-flow descriptions."""

    SPOTTING = "spotting"
    LIGHT = "light"
    MODERATE = "moderate"
    HEAVY = "heavy"


@unique
class CycleSymptom(StrEnum):
    """General user-reported cycle context without diagnostic meaning."""

    CRAMPS = "cramps"
    BLOATING = "bloating"
    HEADACHE = "headache"
    BACK_DISCOMFORT = "back_discomfort"
    BREAST_TENDERNESS = "breast_tenderness"
    FATIGUE = "fatigue"
    MOOD_CHANGE = "mood_change"
    NAUSEA = "nausea"
    ACNE = "acne"
    FOOD_CRAVING = "food_craving"
    SLEEP_CHANGE = "sleep_change"
    OTHER = "other"


@unique
class SymptomIntensity(StrEnum):
    """Optional user-selected symptom intensity without medical severity."""

    MILD = "mild"
    MODERATE = "moderate"
    STRONG = "strong"


@dataclass(frozen=True, slots=True)
class CycleSymptomEntry:
    """One user-reported cycle symptom with optional selected intensity.

    Raises:
        DomainValidationError: If a supplied object is not a controlled type.
    """

    symptom: CycleSymptom
    intensity: SymptomIntensity | None = None

    def __post_init__(self) -> None:
        """Validate controlled values without conversion or inference."""
        if not isinstance(self.symptom, CycleSymptom):
            raise DomainValidationError(f"symptom must be a CycleSymptom; got {self.symptom!r}")
        if self.intensity is not None and not isinstance(
            self.intensity,
            SymptomIntensity,
        ):
            raise DomainValidationError(
                f"intensity must be a SymptomIntensity or None; got {self.intensity!r}"
            )


@dataclass(frozen=True, slots=True)
class MenstrualBleedingRecord:
    """One timestamped, user-reported menstrual bleeding observation.

    ``metadata.recorded_at`` supplies the observation timestamp and metadata
    carries optional notes. Symptoms remain an immutable ordered tuple, with
    each symptom type appearing at most once. Flow and symptoms are recorded
    without inference, diagnosis, prediction, or medical interpretation.

    Raises:
        DomainValidationError: If metadata, flow, or symptoms are invalid.
    """

    metadata: RecordMetadata
    flow: MenstrualFlow
    symptoms: tuple[CycleSymptomEntry, ...] = ()

    def __post_init__(self) -> None:
        """Validate supplied objects and unique ordered symptom entries."""
        if not isinstance(self.metadata, RecordMetadata):
            raise DomainValidationError(f"metadata must be a RecordMetadata; got {self.metadata!r}")
        if not isinstance(self.flow, MenstrualFlow):
            raise DomainValidationError(f"flow must be a MenstrualFlow; got {self.flow!r}")
        if type(self.symptoms) is not tuple:
            raise DomainValidationError(
                f"symptoms must be a tuple of CycleSymptomEntry values; got {self.symptoms!r}"
            )
        if any(not isinstance(entry, CycleSymptomEntry) for entry in self.symptoms):
            raise DomainValidationError(
                f"every symptom must be a CycleSymptomEntry; got {self.symptoms!r}"
            )

        symptom_types = tuple(entry.symptom for entry in self.symptoms)
        if len(set(symptom_types)) != len(symptom_types):
            raise DomainValidationError(
                f"symptoms must not contain duplicate symptom types; got {self.symptoms!r}"
            )

    @property
    def symptom_count(self) -> int:
        """Return the number of unique ordered symptom entries."""
        return len(self.symptoms)

    @property
    def has_symptoms(self) -> bool:
        """Return whether at least one symptom was explicitly reported."""
        return bool(self.symptoms)


@dataclass(frozen=True, slots=True)
class MenstrualCycleRecord:
    """A neutral menstrual-cycle date range supplied directly by a user.

    Dates are never inferred from bleeding observations. An absent end date
    means the range is open or incomplete. The inclusive recorded span is not
    a prediction, regularity classification, fertility analysis, or comparison
    against population or medical norms.

    Raises:
        DomainValidationError: If metadata, a date, or date ordering is invalid.
    """

    metadata: RecordMetadata
    start_date: date
    end_date: date | None = None

    def __post_init__(self) -> None:
        """Validate exact user-supplied dates without parsing or inference."""
        if not isinstance(self.metadata, RecordMetadata):
            raise DomainValidationError(f"metadata must be a RecordMetadata; got {self.metadata!r}")
        if type(self.start_date) is not date:
            raise DomainValidationError(f"start_date must be a plain date; got {self.start_date!r}")
        if self.end_date is not None and type(self.end_date) is not date:
            raise DomainValidationError(
                f"end_date must be a plain date or None; got {self.end_date!r}"
            )
        if self.end_date is not None and self.end_date < self.start_date:
            raise DomainValidationError(
                "end_date must not precede start_date; "
                f"got start_date={self.start_date!r}, end_date={self.end_date!r}"
            )

    @property
    def is_ongoing(self) -> bool:
        """Return whether the user-supplied date range has no end date."""
        return self.end_date is None

    @property
    def cycle_span_days(self) -> int | None:
        """Return the inclusive recorded date span, or ``None`` when open."""
        if self.end_date is None:
            return None
        return (self.end_date - self.start_date).days + 1
