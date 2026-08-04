"""Deterministic descriptive trend calculation for canonical metric samples."""

import statistics
from math import isfinite

from lifelenz.analytics.baselines import (
    MetricSampleExtractor,
    _require_metric,
    _require_profile_id,
    _require_record,
    _require_time_range,
    _WellnessRecord,
)
from lifelenz.analytics.exceptions import (
    AnalyticsValidationError,
    InsufficientTrendDataError,
)
from lifelenz.analytics.models import (
    MetricSample,
    WellnessTrend,
    _classify_direction,
    _finite_float_difference,
)
from lifelenz.domain import MetricIdentifier, ProfileId, TimeRange
from lifelenz.domain.taxonomy import DEFAULT_UNIT_BY_METRIC

_SECONDS_PER_DAY = 86_400.0


def _require_stability_tolerance(value: object) -> float:
    """Require a finite, non-negative plain float without coercion."""
    if type(value) is not float or not isfinite(value) or value < 0.0:
        raise AnalyticsValidationError(
            f"stability_tolerance must be a finite non-negative float; got {value!r}"
        )
    return value


class WellnessTrendCalculator:
    """Calculate purely mathematical trends from canonical observations.

    Matching samples are ordered by timestamp and source identifier. Endpoint
    change and least-squares slope per elapsed day are descriptive only. At
    least two samples are required; no prediction, recommendation, health
    interpretation, correlation, or goal progress is produced.
    """

    def calculate(
        self,
        profile_id: ProfileId,
        metric: MetricIdentifier,
        samples: tuple[MetricSample, ...],
        *,
        time_range: TimeRange | None = None,
        stability_tolerance: float = 0.0,
    ) -> WellnessTrend:
        """Return endpoint change, slope per day, and neutral direction.

        Filtering is start-inclusive and end-exclusive. If every retained
        timestamp represents the same instant, slope is defined as ``0.0`` and
        direction is stable while record-ID ordering still determines endpoints.
        """
        validated_profile_id = _require_profile_id(profile_id)
        validated_metric = _require_metric(metric)
        if type(samples) is not tuple:
            raise AnalyticsValidationError(
                f"samples must be a tuple of MetricSample values; got {samples!r}"
            )
        validated_time_range = _require_time_range(time_range)
        validated_tolerance = _require_stability_tolerance(stability_tolerance)
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
        if len(retained) < 2:
            range_context = (
                " without a time range"
                if validated_time_range is None
                else f" within time range {validated_time_range!r}"
            )
            raise InsufficientTrendDataError(
                f"at least two trend samples are required for profile "
                f"{validated_profile_id.value!r}, metric {validated_metric.value!r}"
                f"{range_context}; got {len(retained)}"
            )

        ordered = tuple(
            sorted(
                retained,
                key=lambda sample: (sample.observed_at, sample.source_record_id.value),
            )
        )
        first = ordered[0]
        last = ordered[-1]
        absolute_change = _finite_float_difference(
            last.value,
            first.value,
            field_name="trend endpoint values",
        )
        percentage_change = (
            None if first.value == 0 else absolute_change / abs(float(first.value)) * 100.0
        )
        slope_per_day = _calculate_slope_per_day(ordered)
        direction = _classify_direction(slope_per_day, validated_tolerance)
        return WellnessTrend(
            profile_id=validated_profile_id,
            metric=validated_metric,
            unit=canonical_unit,
            sample_count=len(ordered),
            first_value=first.value,
            last_value=last.value,
            absolute_change=absolute_change,
            percentage_change=percentage_change,
            slope_per_day=slope_per_day,
            direction=direction,
            stability_tolerance=validated_tolerance,
            first_observed_at=first.observed_at,
            last_observed_at=last.observed_at,
            time_range=validated_time_range,
        )

    def calculate_from_records(
        self,
        profile_id: ProfileId,
        metric: MetricIdentifier,
        records: tuple[_WellnessRecord, ...],
        *,
        time_range: TimeRange | None = None,
        stability_tolerance: float = 0.0,
    ) -> WellnessTrend:
        """Extract supported records and delegate to the trend calculation.

        Existing ``MetricSampleExtractor`` mappings provide canonical values and
        metadata timestamps. No repository, application service, persistence,
        tracked-domain policy, or duplicated extraction mapping is involved.
        """
        validated_profile_id = _require_profile_id(profile_id)
        validated_metric = _require_metric(metric)
        if type(records) is not tuple:
            raise AnalyticsValidationError(
                f"records must be a tuple of supported wellness records; got {records!r}"
            )
        validated_time_range = _require_time_range(time_range)
        validated_tolerance = _require_stability_tolerance(stability_tolerance)
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
            stability_tolerance=validated_tolerance,
        )


def _calculate_slope_per_day(samples: tuple[MetricSample, ...]) -> float:
    """Return least-squares slope per elapsed day for deterministically ordered samples."""
    first_observed_at = samples[0].observed_at
    x_values = tuple(
        (sample.observed_at - first_observed_at).total_seconds() / _SECONDS_PER_DAY
        for sample in samples
    )
    try:
        y_values = tuple(float(sample.value) for sample in samples)
    except OverflowError as error:
        raise AnalyticsValidationError(
            "sample values must support finite floating-point slope calculation"
        ) from error
    mean_x = statistics.fmean(x_values)
    mean_y = statistics.fmean(y_values)
    denominator = sum((x_value - mean_x) ** 2 for x_value in x_values)
    if denominator == 0.0:
        return 0.0
    numerator = sum(
        (x_value - mean_x) * (y_value - mean_y)
        for x_value, y_value in zip(x_values, y_values, strict=True)
    )
    return numerator / denominator
