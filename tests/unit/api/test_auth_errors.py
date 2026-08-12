from fastapi import FastAPI

from lifelenz.api.errors import register_exception_handlers
from lifelenz.application import (
    AccountAlreadyExistsError,
    AccountNotFoundError,
    InactiveAccountError,
    InvalidCredentialsError,
    ProfileAccessDeniedError,
)
from lifelenz.security import TokenValidationError


def test_auth_exception_handlers_are_explicit() -> None:
    app = FastAPI()
    register_exception_handlers(app)
    for exception in (
        AccountAlreadyExistsError,
        AccountNotFoundError,
        InactiveAccountError,
        InvalidCredentialsError,
        ProfileAccessDeniedError,
        TokenValidationError,
    ):
        assert exception in app.exception_handlers
