import asyncio
from pathlib import Path

import httpx

from lifelenz.api import ApiSettings, create_app

SECRET = "record-correction-test-secret-at-least-32-bytes"
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
            "display_name": "Synthetic User",
            "measurement_system": "metric",
            "week_start": "monday",
            "tracked_domains": ["hydration", "nutrition"],
        },
    )
    assert response.status_code == 201


def hydration_payload(
    *,
    volume: float = 250.0,
    notes: str = "Synthetic note",
    source: str = "manual",
) -> dict[str, object]:
    return {
        "record_type": "hydration",
        "metadata": {
            "recorded_at": "2026-08-22T12:00:00+05:30",
            "source": source,
            "notes": notes,
        },
        "data": {
            "volume_milliliters": volume,
            "beverage_type": "water",
            "caffeine_milligrams": 0.0,
        },
    }


def meal_payload() -> dict[str, object]:
    return {
        "record_type": "meal",
        "metadata": {
            "recorded_at": "2026-08-22T12:00:00+05:30",
            "source": "manual",
            "notes": "Synthetic replacement",
        },
        "data": {
            "meal_type": "lunch",
            "nutrition": {"protein_grams": 20.0},
            "name": "Synthetic meal",
        },
    }


def test_record_correction_preserves_identity_type_ownership_and_durability(
    tmp_path: Path,
) -> None:
    database = tmp_path / "record-corrections.db"
    app = create_app(settings(database))

    assert (
        request(
            app,
            "PUT",
            "/api/v1/records/00000000-0000-4000-8000-000000000001",
            json=hydration_payload(),
        ).status_code
        == 401
    )
    assert (
        request(
            app,
            "DELETE",
            "/api/v1/records/00000000-0000-4000-8000-000000000001",
        ).status_code
        == 401
    )

    owner = authorize(app, "record-owner@example.com")
    other = authorize(app, "record-other@example.com")
    create_profile(app, owner)
    create_profile(app, other)

    created = request(
        app,
        "POST",
        "/api/v1/records",
        headers=owner,
        json=hydration_payload(source="csv_import"),
    )
    assert created.status_code == 201
    record_id = created.json()["metadata"]["record_id"]
    assert created.json()["metadata"]["source"] == "csv_import"

    corrected = request(
        app,
        "PUT",
        f"/api/v1/records/{record_id}",
        headers=owner,
        json=hydration_payload(
            volume=475.0,
            notes="  Corrected synthetic note  ",
            source="manual",
        ),
    )
    assert corrected.status_code == 200, corrected.text
    corrected_body = corrected.json()
    assert corrected_body["metadata"]["record_id"] == record_id
    assert corrected_body["metadata"]["source"] == "csv_import"
    assert corrected_body["metadata"]["notes"] == "Corrected synthetic note"
    assert corrected_body["data"]["volume_milliliters"] == 475.0
    assert (
        request(app, "GET", f"/api/v1/records/{record_id}", headers=owner).json()
        == corrected_body
    )

    type_change = request(
        app,
        "PUT",
        f"/api/v1/records/{record_id}",
        headers=owner,
        json=meal_payload(),
    )
    assert (type_change.status_code, type_change.json()["error"]["code"]) == (
        400,
        "application_validation_error",
    )
    assert (
        request(app, "GET", f"/api/v1/records/{record_id}", headers=owner).json()
        == corrected_body
    )

    cross_update = request(
        app,
        "PUT",
        f"/api/v1/records/{record_id}",
        headers=other,
        json=hydration_payload(volume=999.0),
    )
    cross_delete = request(
        app,
        "DELETE",
        f"/api/v1/records/{record_id}",
        headers=other,
    )
    assert {
        (cross_update.status_code, cross_update.json()["error"]["code"]),
        (cross_delete.status_code, cross_delete.json()["error"]["code"]),
    } == {(404, "wellness_record_not_found")}

    restarted = create_app(settings(database))
    owner_token = request(
        restarted,
        "POST",
        "/api/v1/auth/login",
        json={"email": "record-owner@example.com", "password": PASSWORD},
    ).json()["access_token"]
    restarted_owner = {"Authorization": f"Bearer {owner_token}"}
    assert (
        request(
            restarted,
            "GET",
            f"/api/v1/records/{record_id}",
            headers=restarted_owner,
        ).json()
        == corrected_body
    )

    deleted = request(
        restarted,
        "DELETE",
        f"/api/v1/records/{record_id}",
        headers=restarted_owner,
    )
    assert deleted.status_code == 204
    assert deleted.content == b""
    missing = request(
        restarted,
        "GET",
        f"/api/v1/records/{record_id}",
        headers=restarted_owner,
    )
    assert (missing.status_code, missing.json()["error"]["code"]) == (
        404,
        "wellness_record_not_found",
    )

    restarted_again = create_app(settings(database))
    owner_token = request(
        restarted_again,
        "POST",
        "/api/v1/auth/login",
        json={"email": "record-owner@example.com", "password": PASSWORD},
    ).json()["access_token"]
    assert (
        request(
            restarted_again,
            "GET",
            "/api/v1/records",
            headers={"Authorization": f"Bearer {owner_token}"},
        ).json()
        == []
    )


def test_record_correction_openapi_is_bearer_protected_and_discriminated(
    tmp_path: Path,
) -> None:
    schema = create_app(settings(tmp_path / "openapi.db")).openapi()
    record_path = schema["paths"]["/api/v1/records/{record_id}"]
    assert record_path["put"]["security"] == [{"BearerAuth": []}]
    assert record_path["delete"]["security"] == [{"BearerAuth": []}]
    discriminator = record_path["put"]["requestBody"]["content"]["application/json"][
        "schema"
    ]["discriminator"]
    assert set(discriminator["mapping"]) == {
        "sleep",
        "daily_activity",
        "workout",
        "hydration",
        "meal",
        "daily_nutrition",
        "body_measurement",
        "subjective_check_in",
        "menstrual_bleeding",
        "menstrual_cycle",
    }
