import asyncio
from pathlib import Path

import httpx

from lifelenz.api import ApiSettings, create_app

SECRET = "csv-import-test-secret-at-least-32-bytes"
PASSWORD = "correct horse battery staple"


def settings(path: Path) -> ApiSettings:
    return ApiSettings(
        application_name="LifeLenz-AI",
        application_version="0.1.0",
        environment="test",
        database_path=path,
        jwt_secret=SECRET,
    )


def request(app: object, method: str, path: str, **kwargs: object) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)  # type: ignore[arg-type]
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(send())


def authorize(app: object, email: str) -> dict[str, str]:
    assert (
        request(
            app,
            "POST",
            "/api/v1/auth/register",
            json={"email": email, "password": PASSWORD},
        ).status_code
        == 201
    )
    token = request(
        app,
        "POST",
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_profile(app: object, headers: dict[str, str]) -> None:
    response = request(
        app,
        "POST",
        "/api/v1/profile",
        headers=headers,
        json={
            "time_zone": "Asia/Kolkata",
            "display_name": "Synthetic Import User",
            "measurement_system": "metric",
            "week_start": "monday",
            "tracked_domains": [
                "hydration",
                "nutrition",
                "activity",
                "sleep",
                "body_measurements",
                "subjective_check_ins",
            ],
        },
    )
    assert response.status_code == 201, response.text


def import_payload(content: str, *, mode: str = "validate") -> dict[str, object]:
    return {
        "schema_version": 1,
        "record_type": "hydration",
        "mode": mode,
        "content": content,
    }


def test_csv_import_requires_authentication_and_profile(tmp_path: Path) -> None:
    app = create_app(settings(tmp_path / "imports-auth.db"))
    content = "recorded_at,volume_value\n2026-08-20T10:00:00+05:30,500\n"

    unauthenticated = request(
        app,
        "POST",
        "/api/v1/imports/csv",
        json=import_payload(content),
    )
    assert unauthenticated.status_code == 401

    headers = authorize(app, "csv-no-profile@example.com")
    missing_profile = request(
        app,
        "POST",
        "/api/v1/imports/csv",
        headers=headers,
        json=import_payload(content),
    )
    assert (missing_profile.status_code, missing_profile.json()["error"]["code"]) == (
        404,
        "profile_not_configured",
    )


def test_csv_import_validates_deduplicates_and_commits_without_partial_writes(
    tmp_path: Path,
) -> None:
    app = create_app(settings(tmp_path / "imports.db"))
    headers = authorize(app, "csv-owner@example.com")
    create_profile(app, headers)
    repeated = (
        "recorded_at,volume_value,volume_unit,notes\n"
        "2026-08-20T10:00:00+05:30,0.5,liters,Synthetic import\n"
        "2026-08-20T10:00:00+05:30,500,milliliters,Synthetic import\n"
    )

    validation = request(
        app,
        "POST",
        "/api/v1/imports/csv",
        headers=headers,
        json=import_payload(repeated),
    )
    assert validation.status_code == 200, validation.text
    report = validation.json()
    assert report == {
        "schema_version": 1,
        "record_type": "hydration",
        "mode": "validate",
        "total_rows": 2,
        "valid_rows": 2,
        "invalid_rows": 0,
        "duplicate_rows": 1,
        "ready_rows": 1,
        "imported_rows": 0,
        "can_commit": True,
        "issues": [],
        "duplicates": [{"row_number": 3, "reason": "earlier_row"}],
    }
    assert request(app, "GET", "/api/v1/records", headers=headers).json() == []

    committed = request(
        app,
        "POST",
        "/api/v1/imports/csv",
        headers=headers,
        json=import_payload(repeated, mode="commit"),
    )
    assert committed.status_code == 200, committed.text
    assert committed.json()["imported_rows"] == 1
    records = request(app, "GET", "/api/v1/records", headers=headers).json()
    assert len(records) == 1
    assert records[0]["record_type"] == "hydration"
    assert records[0]["metadata"]["source"] == "csv_import"
    assert records[0]["data"]["volume_milliliters"] == 500.0

    repeated_commit = request(
        app,
        "POST",
        "/api/v1/imports/csv",
        headers=headers,
        json=import_payload(repeated, mode="commit"),
    )
    assert repeated_commit.status_code == 200
    assert repeated_commit.json()["duplicate_rows"] == 2
    assert repeated_commit.json()["ready_rows"] == 0
    assert repeated_commit.json()["imported_rows"] == 0
    assert len(request(app, "GET", "/api/v1/records", headers=headers).json()) == 1

    invalid = (
        "recorded_at,volume_value\n"
        "2026-08-20T12:00:00+05:30,250\n"
        "2026-08-20T13:00:00,300\n"
    )
    blocked = request(
        app,
        "POST",
        "/api/v1/imports/csv",
        headers=headers,
        json=import_payload(invalid, mode="commit"),
    )
    assert blocked.status_code == 200
    assert blocked.json()["can_commit"] is False
    assert blocked.json()["valid_rows"] == 1
    assert blocked.json()["invalid_rows"] == 1
    assert blocked.json()["ready_rows"] == 1
    assert blocked.json()["imported_rows"] == 0
    assert blocked.json()["issues"][0]["row_number"] == 3
    assert blocked.json()["issues"][0]["field"] == "recorded_at"
    assert len(request(app, "GET", "/api/v1/records", headers=headers).json()) == 1


def test_csv_import_openapi_is_bearer_protected_and_versioned(tmp_path: Path) -> None:
    schema = create_app(settings(tmp_path / "imports-openapi.db")).openapi()
    operation = schema["paths"]["/api/v1/imports/csv"]["post"]

    assert operation["security"] == [{"BearerAuth": []}]
    request_schema_ref = operation["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    assert request_schema_ref.endswith("/CsvImportRequest")
    import_request = schema["components"]["schemas"]["CsvImportRequest"]
    assert import_request["properties"]["schema_version"]["default"] == 1
    record_type_ref = import_request["properties"]["record_type"]["$ref"]
    record_type_name = record_type_ref.rsplit("/", maxsplit=1)[-1]
    assert set(schema["components"]["schemas"][record_type_name]["enum"]) == {
        "sleep",
        "daily_activity",
        "hydration",
        "daily_nutrition",
        "body_measurement",
        "subjective_check_in",
    }
