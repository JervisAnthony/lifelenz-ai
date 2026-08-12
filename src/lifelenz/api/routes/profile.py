"""Bearer-protected primary wellness-profile routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from lifelenz.api.dependencies import ApiContainer, get_api_container, get_current_user
from lifelenz.api.resource_mapping import profile_from_request, profile_response
from lifelenz.api.resource_schemas import WellnessProfileRequest, WellnessProfileResponse
from lifelenz.api.schemas import ApiErrorResponse
from lifelenz.domain import ProfileId
from lifelenz.identity import UserAccount

ContainerDependency = Annotated[ApiContainer, Depends(get_api_container)]
CurrentUserDependency = Annotated[UserAccount, Depends(get_current_user)]


def create_profile(
    request: WellnessProfileRequest,
    account: CurrentUserDependency,
    container: ContainerDependency,
) -> WellnessProfileResponse:
    profile = profile_from_request(request, profile_id=ProfileId.generate())
    return profile_response(
        container.authenticated_profile_service.create_profile(account.user_id, profile)
    )


def get_profile(
    account: CurrentUserDependency,
    container: ContainerDependency,
) -> WellnessProfileResponse:
    return profile_response(container.authenticated_profile_service.get_profile(account.user_id))


def update_profile(
    request: WellnessProfileRequest,
    account: CurrentUserDependency,
    container: ContainerDependency,
) -> WellnessProfileResponse:
    current = container.authenticated_profile_service.get_profile(account.user_id)
    replacement = profile_from_request(request, profile_id=current.profile_id)
    return profile_response(
        container.authenticated_profile_service.update_profile(account.user_id, replacement)
    )


def create_profile_router() -> APIRouter:
    router = APIRouter(prefix="/profile", tags=["profile"])
    common_errors = {
        401: {"model": ApiErrorResponse},
        404: {"model": ApiErrorResponse},
        422: {"model": ApiErrorResponse},
    }
    router.add_api_route(
        "",
        create_profile,
        methods=["POST"],
        status_code=status.HTTP_201_CREATED,
        response_model=WellnessProfileResponse,
        responses={**common_errors, 409: {"model": ApiErrorResponse}},
        operation_id="profile_create",
        summary="Create primary wellness profile",
    )
    router.add_api_route(
        "",
        get_profile,
        methods=["GET"],
        response_model=WellnessProfileResponse,
        responses=common_errors,
        operation_id="profile_get",
        summary="Get primary wellness profile",
    )
    router.add_api_route(
        "",
        update_profile,
        methods=["PUT"],
        response_model=WellnessProfileResponse,
        responses=common_errors,
        operation_id="profile_update",
        summary="Replace primary wellness profile configuration",
    )
    return router
