"""Immutable domain types for neutral body measurements."""

from dataclasses import dataclass

from lifelenz.domain.exceptions import DomainValidationError
from lifelenz.domain.primitives import RecordMetadata
from lifelenz.domain.validation import require_in_range, require_positive


@dataclass(frozen=True, slots=True)
class BodyMeasurementRecord:
    """One timestamped set of independently recorded body measurements.

    Weight is stored in kilograms, height in meters, body fat as a percentage,
    and waist circumference in centimeters. Optional measurements remain
    unknown when absent. No population category, target, trend, or health
    interpretation is inferred.

    Raises:
        DomainValidationError: If metadata is not a ``RecordMetadata`` value.
        InvalidNumericValueError: If a supplied measurement is invalid.
    """

    metadata: RecordMetadata
    weight_kilograms: int | float
    height_meters: int | float | None = None
    body_fat_percent: int | float | None = None
    waist_circumference_centimeters: int | float | None = None

    def __post_init__(self) -> None:
        """Validate each supplied measurement without coercion or inference."""
        if not isinstance(self.metadata, RecordMetadata):
            raise DomainValidationError(f"metadata must be a RecordMetadata; got {self.metadata!r}")

        require_positive(self.weight_kilograms, field_name="weight_kilograms")
        if self.height_meters is not None:
            require_positive(self.height_meters, field_name="height_meters")
        if self.body_fat_percent is not None:
            require_in_range(
                self.body_fat_percent,
                0,
                100,
                field_name="body_fat_percent",
            )
        if self.waist_circumference_centimeters is not None:
            require_positive(
                self.waist_circumference_centimeters,
                field_name="waist_circumference_centimeters",
            )

    @property
    def bmi(self) -> float | None:
        """Return direct unrounded BMI, or ``None`` when height is unknown."""
        if self.height_meters is None:
            return None
        return self.weight_kilograms / (self.height_meters**2)

    @property
    def weight_grams(self) -> int | float:
        """Return recorded weight converted directly to grams."""
        return self.weight_kilograms * 1000

    @property
    def height_centimeters(self) -> int | float | None:
        """Return recorded height converted to centimeters when known."""
        if self.height_meters is None:
            return None
        return self.height_meters * 100
