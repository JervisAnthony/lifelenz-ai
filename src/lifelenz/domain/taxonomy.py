"""Controlled vocabulary and relationships for LifeLenz wellness data."""

from collections.abc import Mapping
from enum import StrEnum, unique
from types import MappingProxyType


@unique
class WellnessCategory(StrEnum):
    """Top-level categories used to organize wellness metrics."""

    SLEEP = "sleep"
    ACTIVITY = "activity"
    HYDRATION = "hydration"
    NUTRITION = "nutrition"
    BODY = "body"
    MOOD = "mood"
    ENERGY = "energy"
    STRESS = "stress"
    RECOVERY = "recovery"


@unique
class MetricIdentifier(StrEnum):
    """Identifiers for measurements supported by the foundational taxonomy."""

    SLEEP_DURATION = "sleep_duration"
    TIME_IN_BED = "time_in_bed"
    SLEEP_EFFICIENCY = "sleep_efficiency"

    STEPS = "steps"
    DISTANCE = "distance"
    ACTIVE_MINUTES = "active_minutes"
    ACTIVE_CALORIES = "active_calories"

    WATER_INTAKE = "water_intake"

    CALORIES = "calories"
    PROTEIN = "protein"
    CARBOHYDRATES = "carbohydrates"
    FAT = "fat"
    FIBRE = "fibre"

    WEIGHT = "weight"
    HEIGHT = "height"
    BMI = "bmi"
    BODY_FAT = "body_fat"

    MOOD_SCORE = "mood_score"
    ENERGY_SCORE = "energy_score"
    STRESS_SCORE = "stress_score"
    RECOVERY_SCORE = "recovery_score"


@unique
class MeasurementUnit(StrEnum):
    """Units available for normalized wellness measurements."""

    MINUTES = "minutes"
    HOURS = "hours"
    METERS = "meters"
    KILOMETERS = "kilometers"
    GRAMS = "grams"
    KILOGRAMS = "kilograms"
    KILOGRAMS_PER_SQUARE_METER = "kilograms_per_square_meter"
    MILLILITERS = "milliliters"
    LITERS = "liters"
    KCAL = "kcal"
    PERCENT = "percent"
    COUNT = "count"
    SCORE = "score"


@unique
class DataSource(StrEnum):
    """Vendor-neutral origins for wellness data."""

    MANUAL = "manual"
    CSV_IMPORT = "csv_import"
    APP_IMPORT = "app_import"
    API_IMPORT = "api_import"


@unique
class ConfidenceLevel(StrEnum):
    """Qualitative confidence attached to a wellness observation."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@unique
class InsightSeverity(StrEnum):
    """Non-medical importance levels for wellness observations."""

    INFO = "info"
    NOTICE = "notice"
    WARNING = "warning"


METRICS_BY_CATEGORY: Mapping[WellnessCategory, tuple[MetricIdentifier, ...]] = MappingProxyType(
    {
        WellnessCategory.SLEEP: (
            MetricIdentifier.SLEEP_DURATION,
            MetricIdentifier.TIME_IN_BED,
            MetricIdentifier.SLEEP_EFFICIENCY,
        ),
        WellnessCategory.ACTIVITY: (
            MetricIdentifier.STEPS,
            MetricIdentifier.DISTANCE,
            MetricIdentifier.ACTIVE_MINUTES,
            MetricIdentifier.ACTIVE_CALORIES,
        ),
        WellnessCategory.HYDRATION: (MetricIdentifier.WATER_INTAKE,),
        WellnessCategory.NUTRITION: (
            MetricIdentifier.CALORIES,
            MetricIdentifier.PROTEIN,
            MetricIdentifier.CARBOHYDRATES,
            MetricIdentifier.FAT,
            MetricIdentifier.FIBRE,
        ),
        WellnessCategory.BODY: (
            MetricIdentifier.WEIGHT,
            MetricIdentifier.HEIGHT,
            MetricIdentifier.BMI,
            MetricIdentifier.BODY_FAT,
        ),
        WellnessCategory.MOOD: (MetricIdentifier.MOOD_SCORE,),
        WellnessCategory.ENERGY: (MetricIdentifier.ENERGY_SCORE,),
        WellnessCategory.STRESS: (MetricIdentifier.STRESS_SCORE,),
        WellnessCategory.RECOVERY: (MetricIdentifier.RECOVERY_SCORE,),
    }
)
"""Metrics supported by each wellness category, in stable display order."""


DEFAULT_UNIT_BY_METRIC: Mapping[MetricIdentifier, MeasurementUnit] = MappingProxyType(
    {
        MetricIdentifier.SLEEP_DURATION: MeasurementUnit.HOURS,
        MetricIdentifier.TIME_IN_BED: MeasurementUnit.HOURS,
        MetricIdentifier.SLEEP_EFFICIENCY: MeasurementUnit.PERCENT,
        MetricIdentifier.STEPS: MeasurementUnit.COUNT,
        MetricIdentifier.DISTANCE: MeasurementUnit.KILOMETERS,
        MetricIdentifier.ACTIVE_MINUTES: MeasurementUnit.MINUTES,
        MetricIdentifier.ACTIVE_CALORIES: MeasurementUnit.KCAL,
        MetricIdentifier.WATER_INTAKE: MeasurementUnit.MILLILITERS,
        MetricIdentifier.CALORIES: MeasurementUnit.KCAL,
        MetricIdentifier.PROTEIN: MeasurementUnit.GRAMS,
        MetricIdentifier.CARBOHYDRATES: MeasurementUnit.GRAMS,
        MetricIdentifier.FAT: MeasurementUnit.GRAMS,
        MetricIdentifier.FIBRE: MeasurementUnit.GRAMS,
        MetricIdentifier.WEIGHT: MeasurementUnit.KILOGRAMS,
        MetricIdentifier.HEIGHT: MeasurementUnit.METERS,
        MetricIdentifier.BMI: MeasurementUnit.KILOGRAMS_PER_SQUARE_METER,
        MetricIdentifier.BODY_FAT: MeasurementUnit.PERCENT,
        MetricIdentifier.MOOD_SCORE: MeasurementUnit.SCORE,
        MetricIdentifier.ENERGY_SCORE: MeasurementUnit.SCORE,
        MetricIdentifier.STRESS_SCORE: MeasurementUnit.SCORE,
        MetricIdentifier.RECOVERY_SCORE: MeasurementUnit.SCORE,
    }
)
"""Default normalized measurement unit for every supported metric."""
