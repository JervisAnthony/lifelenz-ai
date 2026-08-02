"""Tests for neutral body-measurement domain records."""

from dataclasses import FrozenInstanceError, fields
from datetime import UTC, datetime

import pytest

from lifelenz import domain
from lifelenz.domain import (
    BeverageType,
    BodyMeasurementRecord,
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
    """Return valid metadata for body measurements."""
    return RecordMetadata(
        record_id=RecordId("body-measurement-1"),
        recorded_at=datetime(2026, 8, 5, 7, 30, tzinfo=UTC),
        source=DataSource.MANUAL,
        notes="Morning measurement",
    )


def _record(
    *,
    metadata: RecordMetadata | None = None,
    weight_kilograms: int | float = 70,
    height_meters: int | float | None = None,
    body_fat_percent: int | float | None = None,
    waist_circumference_centimeters: int | float | None = None,
) -> BodyMeasurementRecord:
    """Build a body record while keeping test setup concise."""
    return BodyMeasurementRecord(
        metadata=metadata or _metadata(),
        weight_kilograms=weight_kilograms,
        height_meters=height_meters,
        body_fat_percent=body_fat_percent,
        waist_circumference_centimeters=waist_circumference_centimeters,
    )


def test_body_measurement_accepts_weight_only() -> None:
    """Weight is the only required measurement."""
    record = _record(weight_kilograms=72.5)

    assert record.weight_kilograms == 72.5
    assert record.height_meters is None
    assert record.body_fat_percent is None
    assert record.waist_circumference_centimeters is None


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("height_meters", 1.75),
        ("body_fat_percent", 22.5),
        ("waist_circumference_centimeters", 81),
    ],
)
def test_body_measurement_accepts_each_optional_measurement(
    field_name: str,
    value: int | float,
) -> None:
    """Every optional measurement may be recorded independently."""
    record = _record(**{field_name: value})  # type: ignore[arg-type]

    assert getattr(record, field_name) == value


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("height_meters", 2),
        ("height_meters", 1.75),
        ("height_meters", 0.001),
        ("waist_circumference_centimeters", 80),
        ("waist_circumference_centimeters", 80.5),
        ("waist_circumference_centimeters", 0.001),
    ],
)
def test_body_measurement_accepts_positive_height_and_waist_values(
    field_name: str,
    value: int | float,
) -> None:
    """Known height and waist accept integers, floats, and small decimals."""
    assert getattr(_record(**{field_name: value}), field_name) == value  # type: ignore[arg-type]


def test_body_measurement_accepts_all_measurements_and_preserves_values() -> None:
    """Mixed numeric types and shared metadata remain exactly as supplied."""
    metadata = _metadata()
    record = _record(
        metadata=metadata,
        weight_kilograms=70,
        height_meters=1.75,
        body_fat_percent=20,
        waist_circumference_centimeters=82.5,
    )

    assert record.metadata is metadata
    assert record.weight_kilograms == 70
    assert isinstance(record.weight_kilograms, int)
    assert record.height_meters == 1.75
    assert isinstance(record.height_meters, float)
    assert record.body_fat_percent == 20
    assert record.waist_circumference_centimeters == 82.5


@pytest.mark.parametrize("weight_kilograms", [1, 0.001, 72, 72.25, 1_000_000])
def test_body_measurement_accepts_positive_uncapped_weight(
    weight_kilograms: int | float,
) -> None:
    """Positive finite integer and float weights have no arbitrary maximum."""
    assert _record(weight_kilograms=weight_kilograms).weight_kilograms == weight_kilograms


@pytest.mark.parametrize("body_fat_percent", [0, 0.0, 50, 100, 100.0])
def test_body_measurement_accepts_inclusive_body_fat_boundaries(
    body_fat_percent: int | float,
) -> None:
    """Recorded body-fat percentages include both endpoints."""
    assert _record(body_fat_percent=body_fat_percent).body_fat_percent == body_fat_percent


@pytest.mark.parametrize("metadata", [{}, "metadata", None, MealNutrition(calories_kcal=1)])
def test_body_measurement_rejects_invalid_metadata(metadata: object) -> None:
    """Mappings, text, None, and unrelated domain objects are not converted."""
    with pytest.raises(DomainValidationError, match="metadata must be a RecordMetadata"):
        BodyMeasurementRecord(metadata, 70)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "value",
    [0, -1, True, "70", float("nan"), float("inf"), float("-inf")],
)
def test_body_measurement_rejects_invalid_weight(value: object) -> None:
    """Required weight must be finite, positive, numeric, and non-boolean."""
    with pytest.raises(InvalidNumericValueError, match="weight_kilograms"):
        _record(weight_kilograms=value)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "field_name",
    ["height_meters", "waist_circumference_centimeters"],
)
@pytest.mark.parametrize(
    "value",
    [0, -1, True, "1", float("nan"), float("inf"), float("-inf")],
)
def test_body_measurement_rejects_invalid_optional_positive_measurements(
    field_name: str,
    value: object,
) -> None:
    """Known height and waist values apply shared positive validation."""
    with pytest.raises(InvalidNumericValueError, match=field_name):
        _record(**{field_name: value})  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "value",
    [-0.1, 100.1, True, "20", float("nan"), float("inf"), float("-inf")],
)
def test_body_measurement_rejects_invalid_body_fat_percent(value: object) -> None:
    """Known body-fat percentages must be finite numbers from zero to 100."""
    with pytest.raises(InvalidNumericValueError, match="body_fat_percent"):
        _record(body_fat_percent=value)  # type: ignore[arg-type]


def test_body_measurement_bmi_is_none_without_height() -> None:
    """Missing height leaves BMI unknown rather than estimated."""
    assert _record(weight_kilograms=70).bmi is None


@pytest.mark.parametrize(
    ("weight_kilograms", "height_meters"),
    [(70, 1.75), (72.5, 1.8), (1, 1), (0.001, 0.001)],
)
def test_body_measurement_bmi_uses_direct_unrounded_arithmetic(
    weight_kilograms: int | float,
    height_meters: int | float,
) -> None:
    """BMI is a neutral deterministic ratio with no rounding or category."""
    record = _record(weight_kilograms=weight_kilograms, height_meters=height_meters)
    expected = weight_kilograms / (height_meters**2)

    assert record.bmi == expected
    assert record.bmi == record.bmi


def test_body_measurement_bmi_is_derived_not_stored() -> None:
    """BMI is computed without storage, classification, advice, or interpretation."""
    record = _record(height_meters=1.75)

    assert "bmi" not in {field.name for field in fields(BodyMeasurementRecord)}
    assert isinstance(record.bmi, (int, float))
    assert not hasattr(record, "bmi_category")
    assert not hasattr(record, "advice")
    assert not hasattr(record, "interpretation")


@pytest.mark.parametrize(
    ("weight_kilograms", "height_meters"),
    [(72, 2), (72.3456, 1.82345)],
)
def test_body_measurement_unit_conversions_are_direct_and_unrounded(
    weight_kilograms: int | float,
    height_meters: int | float,
) -> None:
    """Integer and float metric values convert directly and deterministically."""
    record = _record(weight_kilograms=weight_kilograms, height_meters=height_meters)

    assert record.weight_grams == weight_kilograms * 1000
    assert record.height_centimeters == height_meters * 100
    assert record.weight_grams == record.weight_grams
    assert record.height_centimeters == record.height_centimeters


def test_body_measurement_height_centimeters_is_none_without_height() -> None:
    """Unknown height remains unknown in converted units."""
    assert _record().height_centimeters is None


def test_body_measurement_has_value_equality_and_hashing() -> None:
    """Equivalent measurements are equal immutable hashable values."""
    first = _record(height_meters=1.75, body_fat_percent=20, waist_circumference_centimeters=82)
    same = _record(height_meters=1.75, body_fat_percent=20, waist_circumference_centimeters=82)

    assert first == same
    assert hash(first) == hash(same)


@pytest.mark.parametrize(
    "field_name",
    [
        "metadata",
        "weight_kilograms",
        "height_meters",
        "body_fat_percent",
        "waist_circumference_centimeters",
    ],
)
def test_body_measurement_is_immutable(field_name: str) -> None:
    """Every stored field rejects reassignment."""
    record = _record(height_meters=1.75, body_fat_percent=20, waist_circumference_centimeters=82)

    with pytest.raises(FrozenInstanceError):
        setattr(record, field_name, None)


def test_domain_package_exposes_body_domain_api() -> None:
    """Public exports preserve every prior and body-domain type."""
    expected_exports = {
        "BeverageType": BeverageType,
        "BodyMeasurementRecord": BodyMeasurementRecord,
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

    assert set(expected_exports) <= set(domain.__all__)
    for name, expected_object in expected_exports.items():
        assert getattr(domain, name) is expected_object
