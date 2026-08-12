"""Account registration, login, and current-user HTTP routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from lifelenz.api.dependencies import ApiContainer, get_api_container, get_current_user
from lifelenz.api.schemas import (
    AccessTokenResponse,
    ApiErrorResponse,
    CurrentUserResponse,
    LoginRequest,
    RegisterRequest,
    UserAccountResponse,
)
from lifelenz.identity import EmailAddress, UserAccount

ContainerDependency = Annotated[ApiContainer, Depends(get_api_container)]
CurrentUserDependency = Annotated[UserAccount, Depends(get_current_user)]


def register_account(
    request: RegisterRequest, container: ContainerDependency
) -> UserAccountResponse:
    """Create an account only; profiles and ownership remain separate onboarding steps."""
    account = container.authentication_service.register(
        EmailAddress.from_raw(str(request.email)),
        request.password.get_secret_value(),
    )
    return UserAccountResponse(
        user_id=account.user_id.value,
        email=account.email.value,
        is_active=account.is_active,
    )


def login(request: LoginRequest, container: ContainerDependency) -> AccessTokenResponse:
    """Authenticate credentials and issue one short-lived bearer access token."""
    account = container.authentication_service.authenticate(
        EmailAddress.from_raw(str(request.email)),
        request.password.get_secret_value(),
    )
    return AccessTokenResponse(
        access_token=container.access_token_service.issue_token(account.user_id),
        token_type="bearer",
        expires_in=container.settings.access_token_minutes * 60,
    )


def current_user(
    account: CurrentUserDependency,
    container: ContainerDependency,
) -> CurrentUserResponse:
    """Return authoritative identity and ownership identifiers without wellness content."""
    profile_ids = container.profile_ownership_service.list_profile_ids(account.user_id)
    return CurrentUserResponse(
        user_id=account.user_id.value,
        email=account.email.value,
        is_active=account.is_active,
        profile_ids=tuple(UUID(profile_id.value) for profile_id in profile_ids),
    )


def create_auth_router() -> APIRouter:
    """Build fresh version-relative authentication routes."""
    router = APIRouter(prefix="/auth", tags=["authentication"])
    router.add_api_route(
        "/register",
        register_account,
        methods=["POST"],
        status_code=status.HTTP_201_CREATED,
        response_model=UserAccountResponse,
        responses={409: {"model": ApiErrorResponse}, 422: {"model": ApiErrorResponse}},
        operation_id="auth_register",
        summary="Register account",
    )
    router.add_api_route(
        "/login",
        login,
        methods=["POST"],
        response_model=AccessTokenResponse,
        responses={401: {"model": ApiErrorResponse}, 422: {"model": ApiErrorResponse}},
        operation_id="auth_login",
        summary="Log in",
    )
    router.add_api_route(
        "/me",
        current_user,
        methods=["GET"],
        response_model=CurrentUserResponse,
        responses={401: {"model": ApiErrorResponse}, 403: {"model": ApiErrorResponse}},
        operation_id="auth_me",
        summary="Current user",
    )
    return router
