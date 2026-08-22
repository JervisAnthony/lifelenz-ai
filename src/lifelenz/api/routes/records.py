"""Bearer-protected primary-profile wellness-record routes."""

from dataclasses import replace
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from lifelenz.api.dependencies import ApiContainer, get_api_container, get_current_user
from lifelenz.api.resource_mapping import record_from_request, record_response
from lifelenz.api.resource_schemas import (
    WellnessRecordCreateRequest,
    WellnessRecordResponse,
    WellnessRecordTypeName,
)
from lifelenz.api.schemas import ApiErrorResponse
from lifelenz.application import ApplicationValidationError
from lifelenz.domain import (
    BodyMeasurementRecord,
    DailyActivityRecord,
    DailyNutritionRecord,
    HydrationRecord,
    MealRecord,
    MenstrualBleedingRecord,
    MenstrualCycleRecord,
    RecordId,
    SleepRecord,
    SubjectiveWellnessCheckIn,
    TimeRange,
    WorkoutRecord,
)
from lifelenz.identity import UserAccount
from lifelenz.repositories import WellnessRecord, WellnessRecordType

ContainerDependency = Annotated[ApiContainer, Depends(get_api_container)]
CurrentUserDependency = Annotated[UserAccount, Depends(get_current_user)]

_RECORD_TYPES: dict[WellnessRecordTypeName, WellnessRecordType] = {
    "sleep": SleepRecord,
    "daily_activity": DailyActivityRecord,
    "workout": WorkoutRecord,
    "hydration": HydrationRecord,
    "meal": MealRecord,
    "daily_nutrition": DailyNutritionRecord,
    "body_measurement": BodyMeasurementRecord,
    "subjective_check_in": SubjectiveWellnessCheckIn,
    "menstrual_bleeding": MenstrualBleedingRecord,
    "menstrual_cycle": MenstrualCycleRecord,
}


def create_record(
    request: WellnessRecordCreateRequest,
    account: CurrentUserDependency,
    container: ContainerDependency,
) -> WellnessRecordResponse:
    record = record_from_request(request)
    saved = container.authenticated_wellness_record_service.create_record(
        account.user_id,
        record,
    )
    return record_response(saved)


def list_records(
    account: CurrentUserDependency,
    container: ContainerDependency,
    record_type: Annotated[WellnessRecordTypeName | None, Query()] = None,
    start: Annotated[datetime | None, Query()] = None,
    end: Annotated[datetime | None, Query()] = None,
) -> tuple[WellnessRecordResponse, ...]:
    if (start is None) != (end is None):
        raise ApplicationValidationError("start and end must be supplied together")
    time_range = None if start is None or end is None else TimeRange(start, end)
    domain_type = None if record_type is None else _RECORD_TYPES[record_type]
    records = container.authenticated_wellness_record_service.list_records(
        account.user_id,
        record_type=domain_type,
        time_range=time_range,
    )
    return tuple(record_response(record) for record in records)


def get_record(
    record_id: UUID,
    account: CurrentUserDependency,
    container: ContainerDependency,
) -> WellnessRecordResponse:
    record = container.authenticated_wellness_record_service.get_record(
        account.user_id,
        RecordId(str(record_id)),
    )
    return record_response(record)


def _replacement_record(
    request: WellnessRecordCreateRequest,
    record_id: RecordId,
) -> WellnessRecord:
    generated = record_from_request(request)
    metadata = replace(generated.metadata, record_id=record_id)
    return replace(generated, metadata=metadata)


def update_record(
    record_id: UUID,
    request: WellnessRecordCreateRequest,
    account: CurrentUserDependency,
    container: ContainerDependency,
) -> WellnessRecordResponse:
    validated_id = RecordId(str(record_id))
    replacement = _replacement_record(request, validated_id)
    saved = container.authenticated_wellness_record_service.update_record(
        account.user_id,
        validated_id,
        replacement,
    )
    return record_response(saved)


def delete_record(
    record_id: UUID,
    account: CurrentUserDependency,
    container: ContainerDependency,
) -> Response:
    container.authenticated_wellness_record_service.delete_record(
        account.user_id,
        RecordId(str(record_id)),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def create_records_router() -> APIRouter:
    router = APIRouter(prefix="/records", tags=["records"])
    common_errors = {
        400: {"model": ApiErrorResponse},
        401: {"model": ApiErrorResponse},
        404: {"model": ApiErrorResponse},
        422: {"model": ApiErrorResponse},
    }
    router.add_api_route(
        "",
        create_record,
        methods=["POST"],
        status_code=status.HTTP_201_CREATED,
        response_model=WellnessRecordResponse,
        responses=common_errors,
        operation_id="records_create",
        summary="Create wellness record",
    )
    router.add_api_route(
        "",
        list_records,
        methods=["GET"],
        response_model=tuple[WellnessRecordResponse, ...],
        responses=common_errors,
        operation_id="records_list",
        summary="List wellness records",
    )
    router.add_api_route(
        "/{record_id}",
        get_record,
        methods=["GET"],
        response_model=WellnessRecordResponse,
        responses=common_errors,
        operation_id="records_get",
        summary="Get wellness record",
    )
    router.add_api_route(
        "/{record_id}",
        update_record,
        methods=["PUT"],
        response_model=WellnessRecordResponse,
        responses=common_errors,
        operation_id="records_update",
        summary="Correct wellness record",
    )
    router.add_api_route(
        "/{record_id}",
        delete_record,
        methods=["DELETE"],
        status_code=status.HTTP_204_NO_CONTENT,
        response_model=None,
        responses=common_errors,
        operation_id="records_delete",
        summary="Delete wellness record",
    )
    return router
