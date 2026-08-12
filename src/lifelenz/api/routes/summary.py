"""Bearer-protected structured wellness-summary route."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from lifelenz.api.dependencies import ApiContainer, get_api_container, get_current_user
from lifelenz.api.resource_mapping import summary_response
from lifelenz.api.resource_schemas import WellnessSummaryResponse
from lifelenz.api.schemas import ApiErrorResponse
from lifelenz.application import ApplicationValidationError
from lifelenz.domain import MetricIdentifier, TimeRange
from lifelenz.identity import UserAccount

ContainerDependency = Annotated[ApiContainer, Depends(get_api_container)]
CurrentUserDependency = Annotated[UserAccount, Depends(get_current_user)]


def get_summary(
    account: CurrentUserDependency,
    container: ContainerDependency,
    metrics: Annotated[list[MetricIdentifier] | None, Query(alias="metric")] = None,
    start: Annotated[datetime | None, Query()] = None,
    end: Annotated[datetime | None, Query()] = None,
) -> WellnessSummaryResponse:
    if (start is None) != (end is None):
        raise ApplicationValidationError("start and end must be supplied together")
    time_range = None if start is None or end is None else TimeRange(start, end)
    summary = container.authenticated_wellness_summary_service.create_summary(
        account.user_id,
        metrics=() if metrics is None else tuple(metrics),
        time_range=time_range,
    )
    return summary_response(summary)


def create_summary_router() -> APIRouter:
    router = APIRouter(prefix="/summary", tags=["summary"])
    router.add_api_route(
        "",
        get_summary,
        methods=["GET"],
        response_model=WellnessSummaryResponse,
        responses={
            401: {"model": ApiErrorResponse},
            404: {"model": ApiErrorResponse},
            422: {"model": ApiErrorResponse},
        },
        operation_id="summary_get",
        summary="Get structured wellness summary",
    )
    return router
