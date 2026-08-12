from uuid import uuid4

import pytest
from pydantic import ValidationError

from lifelenz.api.schemas import (
    AccessTokenResponse,
    CurrentUserResponse,
    LoginRequest,
    RegisterRequest,
    UserAccountResponse,
)


def test_requests_validate_email_password_and_hide_secret() -> None:
    request = RegisterRequest(email="User@example.com", password="private passphrase")
    assert request.password.get_secret_value() == "private passphrase"
    assert "private passphrase" not in repr(request)
    for payload in (
        {"email": "invalid", "password": "private passphrase"},
        {"email": "user@example.com", "password": "short"},
        {"email": "user@example.com", "password": "private passphrase", "admin": True},
    ):
        with pytest.raises(ValidationError):
            LoginRequest.model_validate(payload)


def test_responses_have_only_explicit_safe_fields() -> None:
    user_id, profile_id = uuid4(), uuid4()
    assert set(
        UserAccountResponse(user_id=user_id, email="u@example.com", is_active=True).model_dump()
    ) == {"user_id", "email", "is_active"}
    assert (
        AccessTokenResponse(
            access_token="token", token_type="bearer", expires_in=1800
        ).model_dump()["token_type"]
        == "bearer"
    )
    current = CurrentUserResponse(
        user_id=user_id, email="u@example.com", is_active=True, profile_ids=(profile_id,)
    )
    assert current.profile_ids == (profile_id,)
