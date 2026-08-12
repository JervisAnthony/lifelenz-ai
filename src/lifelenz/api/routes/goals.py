"""Bearer-protected primary-profile wellness-goal routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from lifelenz.api.dependencies import ApiContainer, get_api_container, get_current_user
from lifelenz.api.resource_mapping import goal_from_request, goal_response
from lifelenz.api.resource_schemas import WellnessGoalRequest, WellnessGoalResponse
from lifelenz.api.schemas import ApiErrorResponse
from lifelenz.domain import GoalId
from lifelenz.identity import UserAccount

ContainerDependency = Annotated[ApiContainer, Depends(get_api_container)]
CurrentUserDependency = Annotated[UserAccount, Depends(get_current_user)]


def create_goal(
    request: WellnessGoalRequest,
    account: CurrentUserDependency,
    container: ContainerDependency,
) -> WellnessGoalResponse:
    profile = container.authenticated_profile_service.get_profile(account.user_id)
    goal = goal_from_request(
        request,
        goal_id=GoalId.generate(),
        profile_id=profile.profile_id,
    )
    return goal_response(container.authenticated_goal_service.create_goal(account.user_id, goal))


def list_goals(
    account: CurrentUserDependency,
    container: ContainerDependency,
) -> tuple[WellnessGoalResponse, ...]:
    return tuple(
        goal_response(goal)
        for goal in container.authenticated_goal_service.list_goals(account.user_id)
    )


def get_goal(
    goal_id: UUID,
    account: CurrentUserDependency,
    container: ContainerDependency,
) -> WellnessGoalResponse:
    return goal_response(
        container.authenticated_goal_service.get_goal(account.user_id, GoalId(str(goal_id)))
    )


def update_goal(
    goal_id: UUID,
    request: WellnessGoalRequest,
    account: CurrentUserDependency,
    container: ContainerDependency,
) -> WellnessGoalResponse:
    existing = container.authenticated_goal_service.get_goal(
        account.user_id,
        GoalId(str(goal_id)),
    )
    replacement = goal_from_request(
        request,
        goal_id=existing.goal_id,
        profile_id=existing.profile_id,
    )
    return goal_response(
        container.authenticated_goal_service.update_goal(account.user_id, replacement)
    )


def delete_goal(
    goal_id: UUID,
    account: CurrentUserDependency,
    container: ContainerDependency,
) -> Response:
    container.authenticated_goal_service.remove_goal(account.user_id, GoalId(str(goal_id)))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def create_goals_router() -> APIRouter:
    router = APIRouter(prefix="/goals", tags=["goals"])
    common_errors = {
        401: {"model": ApiErrorResponse},
        404: {"model": ApiErrorResponse},
        422: {"model": ApiErrorResponse},
    }
    router.add_api_route(
        "",
        create_goal,
        methods=["POST"],
        status_code=status.HTTP_201_CREATED,
        response_model=WellnessGoalResponse,
        responses=common_errors,
        operation_id="goals_create",
        summary="Create wellness goal",
    )
    router.add_api_route(
        "",
        list_goals,
        methods=["GET"],
        response_model=tuple[WellnessGoalResponse, ...],
        responses=common_errors,
        operation_id="goals_list",
        summary="List wellness goals",
    )
    router.add_api_route(
        "/{goal_id}",
        get_goal,
        methods=["GET"],
        response_model=WellnessGoalResponse,
        responses=common_errors,
        operation_id="goals_get",
        summary="Get wellness goal",
    )
    router.add_api_route(
        "/{goal_id}",
        update_goal,
        methods=["PUT"],
        response_model=WellnessGoalResponse,
        responses=common_errors,
        operation_id="goals_update",
        summary="Replace wellness goal",
    )
    router.add_api_route(
        "/{goal_id}",
        delete_goal,
        methods=["DELETE"],
        status_code=status.HTTP_204_NO_CONTENT,
        responses=common_errors,
        operation_id="goals_delete",
        summary="Delete wellness goal",
    )
    return router
