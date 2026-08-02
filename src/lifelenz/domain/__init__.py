"""Public domain foundations for LifeLenz wellness data."""

from lifelenz.domain.activity import (
    DailyActivityRecord,
    PerceivedExertion,
    WorkoutRecord,
    WorkoutType,
)
from lifelenz.domain.body import BodyMeasurementRecord
from lifelenz.domain.exceptions import (
    DomainValidationError,
    InvalidIdentifierError,
    InvalidNumericValueError,
    InvalidTimeRangeError,
    InvalidTimestampError,
)
from lifelenz.domain.intake import (
    BeverageType,
    DailyNutritionRecord,
    HydrationRecord,
    MealNutrition,
    MealRecord,
    MealType,
)
from lifelenz.domain.primitives import RecordId, RecordMetadata, TimeRange
from lifelenz.domain.sleep import SleepQuality, SleepRecord, SleepStageDurations
from lifelenz.domain.taxonomy import (
    ConfidenceLevel,
    DataSource,
    InsightSeverity,
    MeasurementUnit,
    MetricIdentifier,
    WellnessCategory,
)

__all__ = [
    "BeverageType",
    "BodyMeasurementRecord",
    "ConfidenceLevel",
    "DailyActivityRecord",
    "DailyNutritionRecord",
    "DataSource",
    "DomainValidationError",
    "HydrationRecord",
    "InsightSeverity",
    "InvalidIdentifierError",
    "InvalidNumericValueError",
    "InvalidTimeRangeError",
    "InvalidTimestampError",
    "MealNutrition",
    "MealRecord",
    "MealType",
    "MeasurementUnit",
    "MetricIdentifier",
    "PerceivedExertion",
    "RecordId",
    "RecordMetadata",
    "SleepQuality",
    "SleepRecord",
    "SleepStageDurations",
    "TimeRange",
    "WellnessCategory",
    "WorkoutRecord",
    "WorkoutType",
]
