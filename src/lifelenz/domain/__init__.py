"""Public domain foundations for LifeLenz wellness data."""

from lifelenz.domain.exceptions import (
    DomainValidationError,
    InvalidIdentifierError,
    InvalidNumericValueError,
    InvalidTimeRangeError,
    InvalidTimestampError,
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
    "ConfidenceLevel",
    "DataSource",
    "DomainValidationError",
    "InsightSeverity",
    "InvalidIdentifierError",
    "InvalidNumericValueError",
    "InvalidTimeRangeError",
    "InvalidTimestampError",
    "MeasurementUnit",
    "MetricIdentifier",
    "RecordId",
    "RecordMetadata",
    "SleepQuality",
    "SleepRecord",
    "SleepStageDurations",
    "TimeRange",
    "WellnessCategory",
]
