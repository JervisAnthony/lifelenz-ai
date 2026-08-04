"""Canonical sample extraction and descriptive personal baseline calculation."""

import statistics

from lifelenz.analytics.exceptions import (
    AnalyticsValidationError,
    InsufficientBaselineDataError,
)
from lifelenz.analytics.models import MetricSample, PersonalBaseline
from lifelenz.domain import (
    BodyMeasurementRecord,
    DailyActivityRecord,
    DailyNutritionRecord,
    HydrationRecord,
    MealRecord,
    MenstrualBleedingRecord,
    MenstrualCycleRecord,
    MetricIdentifier,
    ProfileId,
    SleepRecord,
    SubjectiveWellnessCheckIn,
    TimeRange,
    WorkoutRecord,
)
from lifelenz.domain.taxonomy import DEFAULT_UNIT_BY_METRIC

type _WellnessRecord = (
    SleepRecord
    | DailyActivityRecord
    | WorkoutRecord
    | HydrationRecord
    | MealRecord
    | DailyNutritionRecord
    | BodyMeasurementRecord
    | SubjectiveWellnessCheckIn
    | MenstrualBleedingRecord
    | MenstrualCycleRecord
)

_SUPPORTED_RECORD_TYPES = (
    SleepRecord,
    DailyActivityRecord,
    WorkoutRecord,
    HydrationRecord,
    MealRecord,
    DailyNutritionRecord,
    BodyMeasurementRecord,
    SubjectiveWellnessCheckIn,
    MenstrualBleedingRecord,
    MenstrualCycleRecord,
)


def _require_profile_id(profile_id: object) -> ProfileId:
    """Require an existing ProfileId without coercion."""
    if not isinstance(profile_id, ProfileId):
        raise AnalyticsValidationError(f"profile_id must be a ProfileId; got {profile_id!r}")
    return profile_id


def _require_metric(metric: object) -> MetricIdentifier:
    """Require an existing MetricIdentifier without coercion."""
    if not isinstance(metric, MetricIdentifier):
        raise AnalyticsValidationError(f"metric must be a MetricIdentifier; got {metric!r}")
    return metric


def _require_time_range(time_range: object) -> TimeRange | None:
    """Require an existing TimeRange or None without coercion."""
    if time_range is not None and not isinstance(time_range, TimeRange):
        raise AnalyticsValidationError(
            f"time_range must be a TimeRange or None; got {time_range!r}"
        )
    return time_range


def _require_record(record: object) -> _WellnessRecord:
    """Require an exact supported concrete wellness-record type."""
    if type(record) not in _SUPPORTED_RECORD_TYPES:
        raise AnalyticsValidationError(
            f"record must be an exact supported wellness-record type; got {record!r}"
        )
    return record


class MetricSampleExtractor:
    """Extract canonical numeric samples from immutable wellness records.

    Extraction uses ``RecordMetadata.recorded_at`` and ``record_id`` for
    timestamp and traceability. It performs no persistence access or health
    interpretation and emits samples in metric-identifier order.
    """

    def extract(
        self,
        profile_id: ProfileId,
        record: _WellnessRecord,
    ) -> tuple[MetricSample, ...]:
        """Return canonical samples from one exact supported record.

        Sleep minutes are converted once through the record's public
        ``sleep_duration_hours`` property. Meal records are excluded in favor of
        daily nutrition totals, and menstrual records have no direct numeric
        taxonomy mapping in this capability.
        """
        validated_profile_id = _require_profile_id(profile_id)
        validated_record = _require_record(record)

        values: tuple[tuple[MetricIdentifier, int | float], ...]
        if type(validated_record) is SleepRecord:
            values = ((MetricIdentifier.SLEEP_DURATION, validated_record.sleep_duration_hours),)
        elif type(validated_record) is DailyActivityRecord:
            values = (
                (MetricIdentifier.STEPS, validated_record.steps),
                (MetricIdentifier.DISTANCE, validated_record.distance_kilometers),
                (MetricIdentifier.ACTIVE_MINUTES, validated_record.active_minutes),
                (MetricIdentifier.ACTIVE_CALORIES, validated_record.active_calories_kcal),
            )
        elif type(validated_record) is WorkoutRecord:
            values = ((MetricIdentifier.ACTIVE_MINUTES, validated_record.duration_minutes),)
        elif type(validated_record) is HydrationRecord:
            values = ((MetricIdentifier.WATER_INTAKE, validated_record.volume_milliliters),)
        elif type(validated_record) is DailyNutritionRecord:
            nutrition = validated_record.nutrition
            values = tuple(
                (metric, value)
                for metric, value in (
                    (MetricIdentifier.CALORIES, nutrition.calories_kcal),
                    (MetricIdentifier.PROTEIN, nutrition.protein_grams),
                    (MetricIdentifier.CARBOHYDRATES, nutrition.carbohydrates_grams),
                    (MetricIdentifier.FAT, nutrition.fat_grams),
                    (MetricIdentifier.FIBRE, nutrition.fibre_grams),
                )
                if value is not None
            )
        elif type(validated_record) is BodyMeasurementRecord:
            values = tuple(
                (metric, value)
                for metric, value in (
                    (MetricIdentifier.WEIGHT, validated_record.weight_kilograms),
                    (MetricIdentifier.HEIGHT, validated_record.height_meters),
                    (MetricIdentifier.BODY_FAT, validated_record.body_fat_percent),
                )
                if value is not None
            )
        elif type(validated_record) is SubjectiveWellnessCheckIn:
            values = (
                (MetricIdentifier.MOOD_SCORE, validated_record.mood_score.value),
                (MetricIdentifier.ENERGY_SCORE, validated_record.energy_score.value),
                (MetricIdentifier.STRESS_SCORE, validated_record.stress_score.value),
            )
        else:
            values = ()

        metadata = validated_record.metadata
        return tuple(
            MetricSample(
                profile_id=validated_profile_id,
                metric=metric,
                value=value,
                unit=DEFAULT_UNIT_BY_METRIC[metric],
                observed_at=metadata.recorded_at,
                source_record_id=metadata.record_id,
            )
            for metric, value in sorted(values, key=lambda item: item[0].value)
        )


class PersonalBaselineCalculator:
    """Calculate deterministic descriptive baselines from canonical samples.

    Matching samples are filtered by profile, metric, and optional range, then
    ordered by observation timestamp and source identifier. One sample is
    sufficient and produces population standard deviation ``0.0``.
    """

    def calculate(
        self,
        profile_id: ProfileId,
        metric: MetricIdentifier,
        samples: tuple[MetricSample, ...],
        *,
        time_range: TimeRange | None = None,
    ) -> PersonalBaseline:
        """Return unrounded descriptive statistics for matching samples.

        Filtering is start-inclusive and end-exclusive. No outlier removal,
        trend, correlation, recommendation, or prediction is performed.
        """
        validated_profile_id = _require_profile_id(profile_id)
        validated_metric = _require_metric(metric)
        if type(samples) is not tuple:
            raise AnalyticsValidationError(
                f"samples must be a tuple of MetricSample values; got {samples!r}"
            )
        validated_time_range = _require_time_range(time_range)
        if any(type(sample) is not MetricSample for sample in samples):
            raise AnalyticsValidationError(
                f"every sample must be an exact MetricSample; got {samples!r}"
            )

        retained = tuple(
            sample
            for sample in samples
            if sample.profile_id == validated_profile_id
            and sample.metric is validated_metric
            and (
                validated_time_range is None
                or validated_time_range.start <= sample.observed_at < validated_time_range.end
            )
        )
        canonical_unit = DEFAULT_UNIT_BY_METRIC[validated_metric]
        if any(sample.unit is not canonical_unit for sample in retained):
            raise AnalyticsValidationError(
                f"every retained sample must use canonical unit {canonical_unit.value!r}"
            )
        if not retained:
            range_context = (
                " without a time range"
                if validated_time_range is None
                else f" within time range {validated_time_range!r}"
            )
            raise InsufficientBaselineDataError(
                f"no baseline samples for profile {validated_profile_id.value!r}, "
                f"metric {validated_metric.value!r}{range_context}"
            )

        ordered = tuple(
            sorted(
                retained,
                key=lambda sample: (sample.observed_at, sample.source_record_id.value),
            )
        )
        values = tuple(sample.value for sample in ordered)
        return PersonalBaseline(
            profile_id=validated_profile_id,
            metric=validated_metric,
            unit=canonical_unit,
            sample_count=len(values),
            mean=statistics.fmean(values),
            median=float(statistics.median(values)),
            minimum=min(values),
            maximum=max(values),
            population_standard_deviation=float(statistics.pstdev(values)),
            first_observed_at=ordered[0].observed_at,
            last_observed_at=ordered[-1].observed_at,
            time_range=validated_time_range,
        )

    def calculate_from_records(
        self,
        profile_id: ProfileId,
        metric: MetricIdentifier,
        records: tuple[_WellnessRecord, ...],
        *,
        time_range: TimeRange | None = None,
    ) -> PersonalBaseline:
        """Extract records and calculate a baseline with identical semantics.

        Records are associated with the explicitly supplied profile. The method
        performs no repository query and delegates all statistics and
        insufficient-data handling to :meth:`calculate`.
        """
        validated_profile_id = _require_profile_id(profile_id)
        validated_metric = _require_metric(metric)
        if type(records) is not tuple:
            raise AnalyticsValidationError(
                f"records must be a tuple of supported wellness records; got {records!r}"
            )
        validated_time_range = _require_time_range(time_range)
        validated_records = tuple(_require_record(record) for record in records)
        extractor = MetricSampleExtractor()
        samples = tuple(
            sample
            for record in validated_records
            for sample in extractor.extract(validated_profile_id, record)
        )
        return self.calculate(
            validated_profile_id,
            validated_metric,
            samples,
            time_range=validated_time_range,
        )
