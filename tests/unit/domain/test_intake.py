"""Tests for hydration events and basic nutrition domain records."""

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime

import pytest

from lifelenz import domain
from lifelenz.domain import (
    BeverageType,
    ConfidenceLevel,
    DailyActivityRecord,
    DailyNutritionRecord,
    DataSource,
    DomainValidationError,
    HydrationRecord,
    InsightSeverity,
    InvalidIdentifierError,
    InvalidNumericValueError,
    InvalidTimeRangeError,
    InvalidTimestampError,
    MealNutrition,
    MealRecord,
    MealType,
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
    """Return valid timestamped metadata for intake events and summaries."""
    return RecordMetadata(
        record_id=RecordId("intake-record-1"),
        recorded_at=datetime(2026, 8, 4, 12, 30, tzinfo=UTC),
        source=DataSource.MANUAL,
        notes="Recorded by user",
    )


def _nutrition() -> MealNutrition:
    """Return a representative partial nutrition value."""
    return MealNutrition(calories_kcal=450, protein_grams=25.5)


def test_beverage_type_has_exact_stable_ordered_members() -> None:
    """Beverage categories expose the complete neutral serialized vocabulary."""
    expected = [
        ("WATER", "water"),
        ("SPARKLING_WATER", "sparkling_water"),
        ("TEA", "tea"),
        ("COFFEE", "coffee"),
        ("JUICE", "juice"),
        ("MILK", "milk"),
        ("SPORTS_DRINK", "sports_drink"),
        ("OTHER", "other"),
    ]

    assert [(member.name, member.value) for member in BeverageType] == expected
    assert len({member.value for member in BeverageType}) == len(expected)
    assert all(str(member) == member.value for member in BeverageType)


def test_meal_type_has_exact_stable_ordered_members() -> None:
    """Meal types expose the complete general serialized vocabulary."""
    expected = [
        ("BREAKFAST", "breakfast"),
        ("LUNCH", "lunch"),
        ("DINNER", "dinner"),
        ("SNACK", "snack"),
        ("OTHER", "other"),
    ]

    assert [(member.name, member.value) for member in MealType] == expected
    assert len({member.value for member in MealType}) == len(expected)
    assert all(str(member) == member.value for member in MealType)


def test_hydration_accepts_basic_water_intake() -> None:
    """Volume and metadata form a water event with neutral defaults."""
    record = HydrationRecord(_metadata(), 500)

    assert record.volume_milliliters == 500
    assert record.beverage_type is BeverageType.WATER
    assert record.caffeine_milligrams is None
    assert record.has_caffeine is False


@pytest.mark.parametrize("beverage_type", list(BeverageType))
def test_hydration_accepts_every_beverage_type(beverage_type: BeverageType) -> None:
    """Every vendor-neutral beverage category is accepted without interpretation."""
    assert HydrationRecord(_metadata(), 250.5, beverage_type).beverage_type is beverage_type


def test_hydration_preserves_integer_float_and_metadata_values() -> None:
    """Valid source objects and numeric types remain unchanged."""
    metadata = _metadata()
    volume = 375.25
    record = HydrationRecord(metadata, volume, caffeine_milligrams=40)

    assert record.metadata is metadata
    assert record.metadata.recorded_at is metadata.recorded_at
    assert record.volume_milliliters is volume
    assert isinstance(record.caffeine_milligrams, int)


@pytest.mark.parametrize(
    ("caffeine_milligrams", "expected"),
    [(None, False), (0, False), (0.0, False), (75, True), (42.5, True)],
)
def test_hydration_caffeine_indicator_is_neutral_and_explicit(
    caffeine_milligrams: int | float | None,
    expected: bool,
) -> None:
    """The indicator reflects only a supplied positive caffeine measurement."""
    record = HydrationRecord(
        _metadata(),
        300,
        BeverageType.COFFEE,
        caffeine_milligrams,
    )

    assert record.has_caffeine is expected


def test_hydration_volume_liters_is_direct_unrounded_conversion() -> None:
    """Milliliters convert directly to liters without rounding."""
    record = HydrationRecord(_metadata(), 1234.567)

    assert record.volume_liters == 1234.567 / 1000
    assert record.volume_liters == record.volume_liters


def test_hydration_has_value_equality_hashing_and_immutability() -> None:
    """Hydration events are immutable, hashable domain values."""
    first = HydrationRecord(_metadata(), 500, BeverageType.TEA, 30)
    same = HydrationRecord(_metadata(), 500, BeverageType.TEA, 30)

    assert first == same
    assert hash(first) == hash(same)
    with pytest.raises(FrozenInstanceError):
        first.volume_milliliters = 600


def test_hydration_rejects_wrong_metadata_type() -> None:
    """Raw mappings are not converted into metadata."""
    with pytest.raises(DomainValidationError, match="metadata must be a RecordMetadata"):
        HydrationRecord({"record_id": "hydration-1"}, 500)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "volume",
    [0, -1, True, float("nan"), float("inf"), float("-inf")],
)
def test_hydration_rejects_invalid_volume(volume: int | float) -> None:
    """Intake events require finite, positive, non-boolean volume."""
    with pytest.raises(InvalidNumericValueError, match="volume_milliliters"):
        HydrationRecord(_metadata(), volume)


@pytest.mark.parametrize("beverage_type", ["water", DataSource.MANUAL])
def test_hydration_rejects_invalid_beverage_type(beverage_type: object) -> None:
    """Raw strings and unrelated enums are not converted into BeverageType."""
    with pytest.raises(DomainValidationError, match="beverage_type must be a BeverageType"):
        HydrationRecord(_metadata(), 500, beverage_type)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "caffeine",
    [-1, True, float("nan"), float("inf"), float("-inf"), "40"],
)
def test_hydration_rejects_invalid_optional_caffeine(caffeine: object) -> None:
    """Known caffeine must be finite, non-negative, and non-boolean."""
    with pytest.raises(InvalidNumericValueError, match="caffeine_milligrams"):
        HydrationRecord(_metadata(), 500, caffeine_milligrams=caffeine)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "field_name",
    [
        "calories_kcal",
        "protein_grams",
        "carbohydrates_grams",
        "fat_grams",
        "fibre_grams",
    ],
)
def test_meal_nutrition_accepts_each_metric_individually(field_name: str) -> None:
    """Every supported basic metric may be the only known value."""
    nutrition = MealNutrition(**{field_name: 1})  # type: ignore[arg-type]

    assert getattr(nutrition, field_name) == 1
    assert nutrition.known_metric_count == 1


def test_meal_nutrition_accepts_all_metrics_with_mixed_numeric_types() -> None:
    """Complete supplied metrics preserve integer and float representations."""
    nutrition = MealNutrition(
        calories_kcal=600,
        protein_grams=30.5,
        carbohydrates_grams=75,
        fat_grams=20.25,
        fibre_grams=8,
    )

    assert nutrition.calories_kcal == 600
    assert isinstance(nutrition.calories_kcal, int)
    assert nutrition.protein_grams == 30.5
    assert isinstance(nutrition.protein_grams, float)
    assert nutrition.known_metric_count == 5


def test_meal_nutrition_accepts_zero_and_partial_values() -> None:
    """Zero measurements and unknown fields coexist in a partial value."""
    nutrition = MealNutrition(calories_kcal=0, fibre_grams=0.0)

    assert nutrition.calories_kcal == 0
    assert nutrition.fibre_grams == 0.0
    assert nutrition.protein_grams is None
    assert nutrition.known_metric_count == 2


def test_meal_nutrition_does_not_enforce_calorie_macro_formula() -> None:
    """Externally supplied calories and macros remain independent."""
    nutrition = MealNutrition(calories_kcal=1, protein_grams=100, fat_grams=100)

    assert nutrition.calories_kcal == 1
    assert nutrition.protein_grams == 100
    assert nutrition.fat_grams == 100


def test_meal_nutrition_has_value_equality_hashing_and_immutability() -> None:
    """Nutrition measurements are immutable, hashable value objects."""
    first = _nutrition()
    same = _nutrition()

    assert first == same
    assert hash(first) == hash(same)
    with pytest.raises(FrozenInstanceError):
        first.calories_kcal = 500


def test_meal_nutrition_rejects_all_unknown_metrics() -> None:
    """An all-None value cannot represent nutrition information."""
    with pytest.raises(DomainValidationError, match="at least one nutrition metric"):
        MealNutrition()


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        (field_name, value)
        for field_name in (
            "calories_kcal",
            "protein_grams",
            "carbohydrates_grams",
            "fat_grams",
            "fibre_grams",
        )
        for value in (-1, True, float("nan"), float("inf"), float("-inf"), "1")
    ],
)
def test_meal_nutrition_rejects_invalid_known_metrics(field_name: str, value: object) -> None:
    """Every known metric applies shared finite non-negative validation."""
    with pytest.raises(InvalidNumericValueError, match=field_name):
        MealNutrition(**{field_name: value})  # type: ignore[arg-type]


def test_meal_record_accepts_minimum_valid_event() -> None:
    """Timestamped metadata, meal type, and nutrition form a valid event."""
    record = MealRecord(_metadata(), MealType.LUNCH, _nutrition())

    assert record.name is None


@pytest.mark.parametrize("meal_type", list(MealType))
def test_meal_record_accepts_every_meal_type(meal_type: MealType) -> None:
    """Every general meal category is valid without inferred meaning."""
    assert MealRecord(_metadata(), meal_type, _nutrition()).meal_type is meal_type


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        (None, None),
        ("", None),
        (" \t\n", None),
        ("  Oatmeal with fruit  ", "Oatmeal with fruit"),
        ("Vegetable sandwich", "Vegetable sandwich"),
        ("Post-workout snack", "Post-workout snack"),
    ],
)
def test_meal_record_normalizes_optional_descriptive_name(
    name: str | None,
    expected: str | None,
) -> None:
    """Names trim surrounding whitespace and collapse blank text to None."""
    assert MealRecord(_metadata(), MealType.SNACK, _nutrition(), name).name == expected


def test_meal_record_preserves_metadata_and_nutrition() -> None:
    """Validated event context and nutrition are retained unchanged."""
    metadata = _metadata()
    nutrition = _nutrition()
    record = MealRecord(metadata, MealType.DINNER, nutrition)

    assert record.metadata is metadata
    assert record.metadata.recorded_at is metadata.recorded_at
    assert record.nutrition is nutrition
    assert record.metadata.notes == "Recorded by user"


def test_meal_record_has_value_equality_hashing_and_immutability() -> None:
    """Meal events are immutable, hashable domain values after normalization."""
    first = MealRecord(_metadata(), MealType.BREAKFAST, _nutrition(), " Meal ")
    same = MealRecord(_metadata(), MealType.BREAKFAST, _nutrition(), "Meal")

    assert first == same
    assert hash(first) == hash(same)
    with pytest.raises(FrozenInstanceError):
        first.name = "Replacement"


def test_meal_record_rejects_wrong_metadata_type() -> None:
    """Raw mappings are not converted into metadata."""
    with pytest.raises(DomainValidationError, match="metadata must be a RecordMetadata"):
        MealRecord(  # type: ignore[arg-type]
            {"record_id": "meal-1"},
            MealType.LUNCH,
            _nutrition(),
        )


@pytest.mark.parametrize("meal_type", ["lunch", DataSource.MANUAL])
def test_meal_record_rejects_invalid_meal_type(meal_type: object) -> None:
    """Raw strings and unrelated enums are not converted into MealType."""
    with pytest.raises(DomainValidationError, match="meal_type must be a MealType"):
        MealRecord(_metadata(), meal_type, _nutrition())  # type: ignore[arg-type]


def test_meal_record_rejects_wrong_nutrition_type() -> None:
    """Raw mappings are not converted into MealNutrition."""
    with pytest.raises(DomainValidationError, match="nutrition must be a MealNutrition"):
        MealRecord(  # type: ignore[arg-type]
            _metadata(),
            MealType.LUNCH,
            {"calories_kcal": 500},
        )


def test_meal_record_rejects_non_string_name() -> None:
    """Descriptive names accept only text or None."""
    with pytest.raises(DomainValidationError, match="name must be a string or None"):
        MealRecord(_metadata(), MealType.LUNCH, _nutrition(), 123)  # type: ignore[arg-type]


@pytest.mark.parametrize("meal_count", [None, 0, 3])
def test_daily_nutrition_accepts_known_and_unknown_meal_counts(
    meal_count: int | None,
) -> None:
    """Unknown, zero, and positive plain integer meal counts are valid."""
    record = DailyNutritionRecord(
        _metadata(),
        date(2026, 8, 4),
        MealNutrition(protein_grams=25),
        meal_count,
    )

    assert record.meal_count == meal_count


def test_daily_nutrition_preserves_metadata_date_and_partial_nutrition() -> None:
    """Reporting context and partial totals remain unchanged."""
    metadata = _metadata()
    nutrition_date = date(2026, 8, 4)
    nutrition = MealNutrition(fibre_grams=10)
    record = DailyNutritionRecord(metadata, nutrition_date, nutrition)

    assert record.metadata is metadata
    assert record.nutrition_date is nutrition_date
    assert record.nutrition is nutrition


def test_daily_nutrition_has_value_equality_hashing_and_immutability() -> None:
    """Daily summaries are immutable, hashable domain values."""
    first = DailyNutritionRecord(_metadata(), date(2026, 8, 4), _nutrition(), 3)
    same = DailyNutritionRecord(_metadata(), date(2026, 8, 4), _nutrition(), 3)

    assert first == same
    assert hash(first) == hash(same)
    with pytest.raises(FrozenInstanceError):
        first.meal_count = 4


def test_daily_nutrition_rejects_wrong_metadata_type() -> None:
    """Raw mappings are not converted into metadata."""
    with pytest.raises(DomainValidationError, match="metadata must be a RecordMetadata"):
        DailyNutritionRecord(  # type: ignore[arg-type]
            {"record_id": "nutrition-1"},
            date(2026, 8, 4),
            _nutrition(),
        )


@pytest.mark.parametrize("nutrition_date", [datetime(2026, 8, 4, tzinfo=UTC), "2026-08-04"])
def test_daily_nutrition_rejects_non_plain_dates(nutrition_date: object) -> None:
    """Datetimes and strings are rejected rather than converted to reporting dates."""
    with pytest.raises(DomainValidationError, match="nutrition_date must be a plain date"):
        DailyNutritionRecord(  # type: ignore[arg-type]
            _metadata(),
            nutrition_date,
            _nutrition(),
        )


def test_daily_nutrition_rejects_wrong_nutrition_type() -> None:
    """Raw mappings are not converted into nutrition values."""
    with pytest.raises(DomainValidationError, match="nutrition must be a MealNutrition"):
        DailyNutritionRecord(  # type: ignore[arg-type]
            _metadata(),
            date(2026, 8, 4),
            {"calories_kcal": 500},
        )


@pytest.mark.parametrize("meal_count", [-1, 1.5, True, "3"])
def test_daily_nutrition_rejects_invalid_meal_count(meal_count: object) -> None:
    """Known meal counts require non-negative plain integers."""
    with pytest.raises(InvalidNumericValueError, match=r"meal_count.*non-negative plain integer"):
        DailyNutritionRecord(  # type: ignore[arg-type]
            _metadata(),
            date(2026, 8, 4),
            _nutrition(),
            meal_count,
        )


def test_domain_package_exposes_complete_intake_domain_api() -> None:
    """The authoritative export list preserves every prior and intake type."""
    expected_exports = {
        "BeverageType": BeverageType,
        "ConfidenceLevel": ConfidenceLevel,
        "DailyActivityRecord": DailyActivityRecord,
        "DailyNutritionRecord": DailyNutritionRecord,
        "DataSource": DataSource,
        "DomainValidationError": DomainValidationError,
        "HydrationRecord": HydrationRecord,
        "InsightSeverity": InsightSeverity,
        "InvalidIdentifierError": InvalidIdentifierError,
        "InvalidNumericValueError": InvalidNumericValueError,
        "InvalidTimeRangeError": InvalidTimeRangeError,
        "InvalidTimestampError": InvalidTimestampError,
        "MealNutrition": MealNutrition,
        "MealRecord": MealRecord,
        "MealType": MealType,
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

    assert domain.__all__ == list(expected_exports)
    for name, expected_object in expected_exports.items():
        assert getattr(domain, name) is expected_object
