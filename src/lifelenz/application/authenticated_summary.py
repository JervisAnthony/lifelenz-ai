"""Account-scoped access to existing deterministic wellness summaries."""

from lifelenz.application.authenticated_profile import AuthenticatedProfileService
from lifelenz.application.exceptions import (
    ApplicationValidationError,
    WellnessSummaryUnavailableError,
)
from lifelenz.application.summaries import WellnessSummary, WellnessSummaryService
from lifelenz.domain import MetricIdentifier, TimeRange
from lifelenz.identity import UserId


class AuthenticatedWellnessSummaryService:
    """Resolve ownership before delegating all analytics to WellnessSummaryService."""

    def __init__(
        self,
        profile_service: AuthenticatedProfileService,
        summary_service: WellnessSummaryService,
    ) -> None:
        if not isinstance(profile_service, AuthenticatedProfileService):
            raise ApplicationValidationError(
                "profile_service must be an AuthenticatedProfileService"
            )
        if not isinstance(summary_service, WellnessSummaryService):
            raise ApplicationValidationError("summary_service must be a WellnessSummaryService")
        self._profile_service = profile_service
        self._summary_service = summary_service

    def create_summary(
        self,
        user_id: UserId,
        *,
        metrics: tuple[MetricIdentifier, ...] = (),
        time_range: TimeRange | None = None,
    ) -> WellnessSummary:
        """Create an owned summary and optionally select explicitly requested metrics."""
        selected = self._require_metrics(metrics)
        profile = self._profile_service.get_profile(user_id)
        summary = self._summary_service.create_summary(
            profile.profile_id,
            time_range=time_range,
        )
        if not selected:
            return summary
        retained = tuple(item for item in summary.metrics if item.metric in selected)
        if not retained:
            raise WellnessSummaryUnavailableError(
                "no supported wellness observations for the selected metrics"
            )
        return WellnessSummary(
            profile=summary.profile,
            metrics=retained,
            time_range=summary.time_range,
            generated_from_record_count=summary.generated_from_record_count,
        )

    @staticmethod
    def _require_metrics(metrics: object) -> tuple[MetricIdentifier, ...]:
        if type(metrics) is not tuple or any(
            not isinstance(metric, MetricIdentifier) for metric in metrics
        ):
            raise ApplicationValidationError("metrics must be a tuple of MetricIdentifier values")
        if len(set(metrics)) != len(metrics):
            raise ApplicationValidationError("metrics must not contain duplicates")
        return metrics
