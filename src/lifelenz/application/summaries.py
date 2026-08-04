"""Structured application workflow combining records, baselines, and trends."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import isfinite

from lifelenz.analytics import (
    MetricSample,
    MetricSampleExtractor,
    PersonalBaseline,
    PersonalBaselineCalculator,
    WellnessTrend,
    WellnessTrendCalculator,
)
from lifelenz.application.exceptions import (
    ApplicationValidationError,
    ProfileNotFoundError,
    WellnessSummaryUnavailableError,
)
from lifelenz.application.services import (
    _PROFILE_REPOSITORY_SHAPE,
    _RECORD_REPOSITORY_SHAPE,
    _require_repository,
)
from lifelenz.domain import (
    MeasurementUnit,
    MetricIdentifier,
    ProfileId,
    TimeRange,
    WellnessProfile,
)
from lifelenz.domain.taxonomy import DEFAULT_UNIT_BY_METRIC
from lifelenz.repositories import (
    EntityNotFoundError,
    ProfileRepository,
    WellnessRecord,
    WellnessRecordRepository,
)


def _validation_error(
    field_name: str, requirement: str, value: object
) -> ApplicationValidationError:
    return ApplicationValidationError(f"{field_name} must {requirement}; got {value!r}")


@dataclass(frozen=True, slots=True)
class MetricWellnessSummary:
    """Structured baseline and optional trend for one profile-owned canonical metric."""

    metric: MetricIdentifier
    unit: MeasurementUnit
    baseline: PersonalBaseline
    trend: WellnessTrend | None

    def __post_init__(self) -> None:
        """Validate canonical-unit and baseline/trend consistency without coercion."""
        if not isinstance(self.metric, MetricIdentifier):
            raise _validation_error("metric", "be a MetricIdentifier", self.metric)
        if not isinstance(self.unit, MeasurementUnit):
            raise _validation_error("unit", "be a MeasurementUnit", self.unit)
        canonical_unit = DEFAULT_UNIT_BY_METRIC[self.metric]
        if self.unit is not canonical_unit:
            raise ApplicationValidationError(
                f"unit must be canonical {canonical_unit.value!r} for metric "
                f"{self.metric.value!r}; got {self.unit!r}"
            )
        if not isinstance(self.baseline, PersonalBaseline):
            raise _validation_error("baseline", "be a PersonalBaseline", self.baseline)
        if self.baseline.metric is not self.metric:
            raise ApplicationValidationError("baseline metric must match metric")
        if self.baseline.unit is not self.unit:
            raise ApplicationValidationError("baseline unit must match unit")

        if self.trend is None:
            if self.baseline.sample_count != 1:
                raise ApplicationValidationError(
                    "trend may be None only when baseline sample_count is one"
                )
            return
        if not isinstance(self.trend, WellnessTrend):
            raise _validation_error("trend", "be a WellnessTrend or None", self.trend)
        if self.trend.profile_id != self.baseline.profile_id:
            raise ApplicationValidationError("trend profile_id must match baseline profile_id")
        if self.trend.metric is not self.metric:
            raise ApplicationValidationError("trend metric must match metric")
        if self.trend.unit is not self.unit:
            raise ApplicationValidationError("trend unit must match unit")
        if self.trend.time_range != self.baseline.time_range:
            raise ApplicationValidationError("trend time_range must match baseline time_range")
        if self.trend.sample_count != self.baseline.sample_count:
            raise ApplicationValidationError("trend sample_count must match baseline sample_count")
        if self.trend.first_observed_at < self.baseline.first_observed_at:
            raise ApplicationValidationError(
                "trend first_observed_at must fall within baseline observation bounds"
            )
        if self.trend.last_observed_at > self.baseline.last_observed_at:
            raise ApplicationValidationError(
                "trend last_observed_at must fall within baseline observation bounds"
            )

    @property
    def profile_id(self) -> ProfileId:
        """Return the profile identifier carried by the baseline."""
        return self.baseline.profile_id

    @property
    def sample_count(self) -> int:
        """Return the number of observations represented by the baseline."""
        return self.baseline.sample_count

    @property
    def has_trend(self) -> bool:
        """Return whether at least two observations produced a trend."""
        return self.trend is not None

    @property
    def first_observed_at(self) -> datetime:
        """Return the baseline's first observation timestamp."""
        return self.baseline.first_observed_at

    @property
    def last_observed_at(self) -> datetime:
        """Return the baseline's last observation timestamp."""
        return self.baseline.last_observed_at

    @property
    def observation_span(self) -> timedelta:
        """Return the baseline's exact observation span."""
        return self.baseline.observation_span


@dataclass(frozen=True, slots=True)
class WellnessSummary:
    """Immutable structured analytics summary for one exact wellness profile."""

    profile: WellnessProfile
    metrics: tuple[MetricWellnessSummary, ...]
    time_range: TimeRange | None
    generated_from_record_count: int

    def __post_init__(self) -> None:
        """Validate ownership, requested context, record count, and metric ordering."""
        if not isinstance(self.profile, WellnessProfile):
            raise _validation_error("profile", "be a WellnessProfile", self.profile)
        if type(self.metrics) is not tuple:
            raise _validation_error(
                "metrics", "be a tuple of MetricWellnessSummary values", self.metrics
            )
        if not self.metrics:
            raise ApplicationValidationError("metrics must contain at least one metric summary")
        if any(
            type(metric_summary) is not MetricWellnessSummary for metric_summary in self.metrics
        ):
            raise _validation_error(
                "metrics", "contain only exact MetricWellnessSummary values", self.metrics
            )
        if self.time_range is not None and not isinstance(self.time_range, TimeRange):
            raise _validation_error("time_range", "be a TimeRange or None", self.time_range)
        if (
            type(self.generated_from_record_count) is not int
            or self.generated_from_record_count < 1
        ):
            raise _validation_error(
                "generated_from_record_count",
                "be a positive plain integer",
                self.generated_from_record_count,
            )

        metric_identifiers = tuple(summary.metric for summary in self.metrics)
        if len(set(metric_identifiers)) != len(metric_identifiers):
            raise ApplicationValidationError(
                "metrics must not contain duplicate metric identifiers"
            )
        if any(summary.profile_id != self.profile.profile_id for summary in self.metrics):
            raise ApplicationValidationError(
                "every metric summary must belong to profile.profile_id"
            )
        if any(summary.baseline.time_range != self.time_range for summary in self.metrics):
            raise ApplicationValidationError(
                "every metric summary time_range must match time_range"
            )
        if metric_identifiers != tuple(sorted(metric_identifiers, key=lambda metric: metric.value)):
            raise ApplicationValidationError("metrics must be ordered by metric.value ascending")

    @property
    def profile_id(self) -> ProfileId:
        """Return the summarized profile's identifier."""
        return self.profile.profile_id

    @property
    def metric_count(self) -> int:
        """Return the number of canonical metric summaries."""
        return len(self.metrics)

    @property
    def metrics_with_trends(self) -> tuple[MetricWellnessSummary, ...]:
        """Return metric summaries with trends in deterministic metric order."""
        return tuple(summary for summary in self.metrics if summary.has_trend)

    @property
    def metrics_without_trends(self) -> tuple[MetricWellnessSummary, ...]:
        """Return metric summaries without trends in deterministic metric order."""
        return tuple(summary for summary in self.metrics if not summary.has_trend)

    @property
    def first_observed_at(self) -> datetime:
        """Return the earliest baseline observation across all metrics."""
        return min(summary.first_observed_at for summary in self.metrics)

    @property
    def last_observed_at(self) -> datetime:
        """Return the latest baseline observation across all metrics."""
        return max(summary.last_observed_at for summary in self.metrics)

    @property
    def observation_span(self) -> timedelta:
        """Return the exact span between the summary's outer observation bounds."""
        return self.last_observed_at - self.first_observed_at


class WellnessSummaryService:
    """Coordinate profile records and descriptive analytics into a structured summary."""

    def __init__(
        self,
        profile_repository: ProfileRepository,
        record_repository: WellnessRecordRepository,
    ) -> None:
        """Require protocol-compatible repositories and retain them privately."""
        _require_repository(
            profile_repository,
            argument_name="profile_repository",
            contract_name="ProfileRepository",
            shape=_PROFILE_REPOSITORY_SHAPE,
        )
        _require_repository(
            record_repository,
            argument_name="record_repository",
            contract_name="WellnessRecordRepository",
            shape=_RECORD_REPOSITORY_SHAPE,
        )
        self._profile_repository = profile_repository
        self._record_repository = record_repository

    def create_summary(
        self,
        profile_id: ProfileId,
        *,
        time_range: TimeRange | None = None,
        trend_stability_tolerance: float = 0.0,
    ) -> WellnessSummary:
        """Return a deterministic summary or report missing profile or summary data.

        Optional metadata-time filtering is delegated to the record repository.
        Every extracted metric receives a canonical baseline; metrics with at least
        two samples also receive a trend using the caller-supplied tolerance. The
        result contains no recommendation, health interpretation, prediction, or
        goal progress.
        """
        validated_profile_id = self._require_profile_id(profile_id)
        validated_time_range = self._require_time_range(time_range)
        validated_tolerance = self._require_tolerance(trend_stability_tolerance)

        try:
            profile = self._profile_repository.get(validated_profile_id)
        except EntityNotFoundError as error:
            raise ProfileNotFoundError(
                f"wellness profile not found for profile_id={validated_profile_id.value!r}"
            ) from error

        records = self._list_records(validated_profile_id, validated_time_range)
        if not records:
            raise self._summary_unavailable(validated_profile_id, validated_time_range)

        extractor = MetricSampleExtractor()
        samples = tuple(
            sample
            for record in records
            for sample in extractor.extract(validated_profile_id, record)
        )
        if not samples:
            raise self._summary_unavailable(validated_profile_id, validated_time_range)

        grouped: dict[MetricIdentifier, list[MetricSample]] = {}
        for sample in samples:
            grouped.setdefault(sample.metric, []).append(sample)

        baseline_calculator = PersonalBaselineCalculator()
        trend_calculator = WellnessTrendCalculator()
        metric_summaries = tuple(
            self._create_metric_summary(
                validated_profile_id,
                metric,
                tuple(grouped[metric]),
                validated_time_range,
                validated_tolerance,
                baseline_calculator,
                trend_calculator,
            )
            for metric in sorted(grouped, key=lambda identifier: identifier.value)
        )
        return WellnessSummary(
            profile=profile,
            metrics=metric_summaries,
            time_range=validated_time_range,
            generated_from_record_count=len(records),
        )

    def _list_records(
        self,
        profile_id: ProfileId,
        time_range: TimeRange | None,
    ) -> tuple[WellnessRecord, ...]:
        if time_range is None:
            return self._record_repository.list_for_profile(profile_id)
        return self._record_repository.list_in_time_range(profile_id, time_range)

    @staticmethod
    def _create_metric_summary(
        profile_id: ProfileId,
        metric: MetricIdentifier,
        samples: tuple[MetricSample, ...],
        time_range: TimeRange | None,
        tolerance: float,
        baseline_calculator: PersonalBaselineCalculator,
        trend_calculator: WellnessTrendCalculator,
    ) -> MetricWellnessSummary:
        baseline = baseline_calculator.calculate(
            profile_id,
            metric,
            samples,
            time_range=time_range,
        )
        trend = (
            trend_calculator.calculate(
                profile_id,
                metric,
                samples,
                time_range=time_range,
                stability_tolerance=tolerance,
            )
            if len(samples) >= 2
            else None
        )
        return MetricWellnessSummary(
            metric=metric,
            unit=DEFAULT_UNIT_BY_METRIC[metric],
            baseline=baseline,
            trend=trend,
        )

    @staticmethod
    def _require_profile_id(profile_id: object) -> ProfileId:
        if not isinstance(profile_id, ProfileId):
            raise _validation_error("profile_id", "be a ProfileId", profile_id)
        return profile_id

    @staticmethod
    def _require_time_range(time_range: object) -> TimeRange | None:
        if time_range is not None and not isinstance(time_range, TimeRange):
            raise _validation_error("time_range", "be a TimeRange or None", time_range)
        return time_range

    @staticmethod
    def _require_tolerance(tolerance: object) -> float:
        if type(tolerance) not in (int, float):
            raise _validation_error(
                "trend_stability_tolerance", "be a finite non-negative plain number", tolerance
            )
        try:
            converted = float(tolerance)
        except OverflowError as error:
            raise _validation_error(
                "trend_stability_tolerance", "be a finite non-negative plain number", tolerance
            ) from error
        if not isfinite(converted) or converted < 0.0:
            raise _validation_error(
                "trend_stability_tolerance", "be a finite non-negative plain number", tolerance
            )
        return converted

    @staticmethod
    def _summary_unavailable(
        profile_id: ProfileId,
        time_range: TimeRange | None,
    ) -> WellnessSummaryUnavailableError:
        context = "without a time range" if time_range is None else f"within {time_range!r}"
        return WellnessSummaryUnavailableError(
            f"no supported wellness observations for profile_id={profile_id.value!r} {context}"
        )
