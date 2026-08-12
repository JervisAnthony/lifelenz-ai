import asyncio
import sqlite3
from dataclasses import replace
from pathlib import Path

import httpx

from lifelenz.api import ApiSettings, create_app
from lifelenz.domain import ProfileId
from lifelenz.identity import EmailAddress

SECRET = "route-test-secret-material-at-least-32-bytes"
PASSWORD = "correct horse battery staple"


def settings(path: Path, **changes: object) -> ApiSettings:
    values = {
        "application_name": "LifeLenz-AI",
        "application_version": "0.1.0",
        "environment": "test",
        "database_path": path,
        "jwt_secret": SECRET,
    }
    values.update(changes)
    return ApiSettings(**values)  # type: ignore[arg-type]


def request(app: object, method: str, path: str, **kwargs: object) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)  # type: ignore[arg-type]
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(send())


def register(app: object, email: str = "User@Example.com") -> httpx.Response:
    return request(
        app, "POST", "/api/v1/auth/register", json={"email": email, "password": PASSWORD}
    )


def login(app: object, email: str = "user@example.com", password: str = PASSWORD) -> httpx.Response:
    return request(app, "POST", "/api/v1/auth/login", json={"email": email, "password": password})


def test_register_creates_account_only_and_case_variant_conflicts(tmp_path: Path) -> None:
    app = create_app(settings(tmp_path / "register.db"))
    response = register(app)
    assert response.status_code == 201
    assert response.json()["email"] == "user@example.com"
    assert set(response.json()) == {"user_id", "email", "is_active"}
    assert app.state.container.profile_repository.list_all() == ()
    assert (
        app.state.container.profile_ownership_repository.list_for_user(
            app.state.container.user_account_repository.get_by_email(
                EmailAddress.from_raw("user@example.com")
            ).user_id
        )
        == ()
    )
    conflict = register(app, " USER@example.com ")
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "account_already_exists"
    assert PASSWORD not in conflict.text


def test_login_failures_are_indistinguishable_and_success_token_is_minimal(tmp_path: Path) -> None:
    app = create_app(settings(tmp_path / "login.db"))
    register(app)
    failures = [
        login(app, password="incorrect horse battery staple"),
        login(app, email="missing@example.com"),
    ]
    assert {
        (r.status_code, r.json()["error"]["code"], r.json()["error"]["message"]) for r in failures
    } == {(401, "invalid_credentials", "Invalid email or password.")}
    success = login(app)
    assert success.status_code == 200
    assert set(success.json()) == {"access_token", "token_type", "expires_in"}
    assert success.json()["token_type"] == "bearer"
    assert success.json()["expires_in"] == 1800


def test_me_checks_database_active_state_and_lists_owned_ids_only(tmp_path: Path) -> None:
    app = create_app(settings(tmp_path / "me.db"))
    register(app)
    token = login(app).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    empty = request(app, "GET", "/api/v1/auth/me", headers=headers)
    assert empty.status_code == 200
    assert empty.json()["profile_ids"] == []
    account = app.state.container.user_account_repository.get_by_email(
        EmailAddress.from_raw("user@example.com")
    )
    profile = ProfileId.generate()
    app.state.container.profile_ownership_repository.assign(account.user_id, profile)
    owned = request(app, "GET", "/api/v1/auth/me", headers=headers)
    assert owned.json()["profile_ids"] == [profile.value]
    app.state.container.user_account_repository.save(replace(account, is_active=False))
    inactive = request(app, "GET", "/api/v1/auth/me", headers=headers)
    assert inactive.status_code == 403
    assert inactive.json()["error"]["code"] == "inactive_account"


def test_removed_token_subject_becomes_invalid_token_not_account_lookup(tmp_path: Path) -> None:
    path = tmp_path / "removed.db"
    app = create_app(settings(path))
    register(app)
    token = login(app).json()["access_token"]
    connection = sqlite3.connect(path)
    connection.execute("DELETE FROM user_accounts")
    connection.commit()
    connection.close()
    response = request(app, "GET", "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_access_token"


def test_custom_prefix_and_openapi_security_are_exact(tmp_path: Path) -> None:
    app = create_app(settings(tmp_path / "custom.db", api_prefix="/service/v1"))
    assert (
        request(
            app,
            "POST",
            "/service/v1/auth/register",
            json={"email": "u@example.com", "password": PASSWORD},
        ).status_code
        == 201
    )
    assert (
        request(
            app,
            "POST",
            "/api/v1/auth/register",
            json={"email": "x@example.com", "password": PASSWORD},
        ).status_code
        == 404
    )
    schema = app.openapi()
    assert set(schema["components"]["securitySchemes"]) == {"BearerAuth"}
    assert schema["paths"]["/service/v1/auth/me"]["get"]["security"] == [{"BearerAuth": []}]
    assert "security" not in schema["paths"]["/service/v1/auth/register"]["post"]
    assert "security" not in schema["paths"]["/service/v1/auth/login"]["post"]
    serialized = str(schema)
    assert SECRET not in serialized
    assert "password_hash" not in serialized
