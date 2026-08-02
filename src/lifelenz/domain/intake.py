"""Immutable domain types for hydration events and basic nutrition records."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum, unique

from lifelenz.domain.exceptions import DomainValidationError, InvalidNumericValueError
from lifelenz.domain.primitives import RecordMetadata
from lifelenz.domain.validation import require_non_negative, require_positive


@unique
class BeverageType(StrEnum):
    """Vendor-neutral beverage categories without health interpretation."""

    WATER = "water"
    SPARKLING_WATER = "sparkling_water"
    TEA = "tea"
    COFFEE = "coffee"
    JUICE = "juice"
    MILK = "milk"
    SPORTS_DRINK = "sports_drink"
    OTHER = "other"


@unique
class MealType(StrEnum):
    """General meal-event categories without culture-specific assumptions."""

    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class HydrationRecord:
    """One timestamped beverage intake event with explicit milliliter volume.

    Optional caffeine is recorded in milligrams as neutral source context. It
    is never inferred from beverage type or interpreted against a threshold.

    Raises:
        DomainValidationError: If metadata or beverage type is invalid.
        InvalidNumericValueError: If volume or optional caffeine is invalid.
    """

    metadata: RecordMetadata
    volume_milliliters: int | float
    beverage_type: BeverageType = BeverageType.WATER
    caffeine_milligrams: int | float | None = None

    def __post_init__(self) -> None:
        """Validate event context and recorded measurements without coercion."""
        if not isinstance(self.metadata, RecordMetadata):
            raise DomainValidationError(f"metadata must be a RecordMetadata; got {self.metadata!r}")
        require_positive(self.volume_milliliters, field_name="volume_milliliters")
        if not isinstance(self.beverage_type, BeverageType):
            raise DomainValidationError(
                f"beverage_type must be a BeverageType; got {self.beverage_type!r}"
            )
        if self.caffeine_milligrams is not None:
            require_non_negative(
                self.caffeine_milligrams,
                field_name="caffeine_milligrams",
            )

    @property
    def volume_liters(self) -> float:
        """Return recorded volume converted directly to unrounded liters."""
        return self.volume_milliliters / 1000

    @property
    def has_caffeine(self) -> bool:
        """Return whether a positive caffeine amount was explicitly recorded."""
        return self.caffeine_milligrams is not None and self.caffeine_milligrams > 0


@dataclass(frozen=True, slots=True)
class MealNutrition:
    """Partial basic nutrition measurements for a meal or daily summary.

    Energy is stored in kcal and macronutrients in grams. At least one metric
    must be known. Values remain independent; calories are never inferred from
    or reconciled with macronutrients.

    Raises:
        DomainValidationError: If every metric is unknown.
        InvalidNumericValueError: If a provided metric is invalid.
    """

    calories_kcal: int | float | None = None
    protein_grams: int | float | None = None
    carbohydrates_grams: int | float | None = None
    fat_grams: int | float | None = None
    fibre_grams: int | float | None = None

    def __post_init__(self) -> None:
        """Validate each known metric without filling missing values."""
        for field_name in (
            "calories_kcal",
            "protein_grams",
            "carbohydrates_grams",
            "fat_grams",
            "fibre_grams",
        ):
            value = getattr(self, field_name)
            if value is not None:
                require_non_negative(value, field_name=field_name)

        if self.known_metric_count == 0:
            raise DomainValidationError("at least one nutrition metric must be provided")

    @property
    def known_metric_count(self) -> int:
        """Return the number of nutrition measurements that are not ``None``."""
        return sum(
            value is not None
            for value in (
                self.calories_kcal,
                self.protein_grams,
                self.carbohydrates_grams,
                self.fat_grams,
                self.fibre_grams,
            )
        )


@dataclass(frozen=True, slots=True)
class MealRecord:
    """One timestamped meal event with partial basic nutrition data.

    ``metadata.recorded_at`` supplies the event timestamp. An optional name is
    descriptive only: non-empty text is trimmed and blank text becomes ``None``.

    Raises:
        DomainValidationError: If metadata, meal type, nutrition, or name is invalid.
    """

    metadata: RecordMetadata
    meal_type: MealType
    nutrition: MealNutrition
    name: str | None = None

    def __post_init__(self) -> None:
        """Validate the meal event and apply documented name normalization."""
        if not isinstance(self.metadata, RecordMetadata):
            raise DomainValidationError(f"metadata must be a RecordMetadata; got {self.metadata!r}")
        if not isinstance(self.meal_type, MealType):
            raise DomainValidationError(f"meal_type must be a MealType; got {self.meal_type!r}")
        if not isinstance(self.nutrition, MealNutrition):
            raise DomainValidationError(
                f"nutrition must be a MealNutrition; got {self.nutrition!r}"
            )
        if self.name is not None and not isinstance(self.name, str):
            raise DomainValidationError(f"name must be a string or None; got {self.name!r}")

        normalized_name = self.name.strip() if self.name is not None else None
        object.__setattr__(self, "name", normalized_name or None)


@dataclass(frozen=True, slots=True)
class DailyNutritionRecord:
    """Basic nutrition totals for an exact reporting date.

    The value may represent a manual, imported, or future aggregated summary;
    this record performs no aggregation, target comparison, or dietary analysis.

    Raises:
        DomainValidationError: If metadata, date, or nutrition is invalid.
        InvalidNumericValueError: If a known meal count is invalid.
    """

    metadata: RecordMetadata
    nutrition_date: date
    nutrition: MealNutrition
    meal_count: int | None = None

    def __post_init__(self) -> None:
        """Validate reporting context, totals, and optional meal count."""
        if not isinstance(self.metadata, RecordMetadata):
            raise DomainValidationError(f"metadata must be a RecordMetadata; got {self.metadata!r}")
        if type(self.nutrition_date) is not date:
            raise DomainValidationError(
                f"nutrition_date must be a plain date; got {self.nutrition_date!r}"
            )
        if not isinstance(self.nutrition, MealNutrition):
            raise DomainValidationError(
                f"nutrition must be a MealNutrition; got {self.nutrition!r}"
            )
        if self.meal_count is not None and (
            type(self.meal_count) is not int or self.meal_count < 0
        ):
            raise InvalidNumericValueError(
                f"meal_count must be a non-negative plain integer or None; got {self.meal_count!r}"
            )
