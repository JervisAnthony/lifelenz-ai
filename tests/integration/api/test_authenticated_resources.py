import asyncio
from copy import deepcopy
from pathlib import Path
from uuid import UUID

import httpx
import pytest

from lifelenz.api import ApiSettings, create_app

SECRET = "authenticated-resource-test-secret-at-least-32-bytes"
PASSWORD = "correct horse battery staple"


def settings(path: Path, *, api_prefix: str = "/api/v1") -> ApiSettings:
    return ApiSettings(
        application_name="LifeLenz-AI",
        application_version="0.1.0",
        environment="test",
        database_path=path,
        jwt_secret=SECRET,
        api_prefix=api_prefix,
    )


def request(app: object, method: str, path: str, **kwargs: object) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)  # type: ignore[arg-type]
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(send())


def authorize(app: object, email: str) -> dict[str, str]:
    registered = request(
        app,
        "POST",
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD},
    )
    assert registered.status_code == 201
    token = request(
        app,
        "POST",
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_profile(
    app: object, headers: dict[str, str], name: str = "Test User"
) -> dict[str, object]:
    response = request(
        app,
        "POST",
        "/api/v1/profile",
        headers=headers,
        json={
            "time_zone": "Asia/Kolkata",
            "display_name": name,
            "measurement_system": "metric",
            "week_start": "monday",
            "tracked_domains": ["sleep", "activity", "hydration", "nutrition"],
        },
    )
    assert response.status_code == 201
    return response.json()


RECORD_SAMPLES = (
    (
        "sleep",
        {
            "period": {
                "start": "2026-01-01T00:00:00+05:30",
                "end": "2026-01-01T08:00:00+05:30",
            },
            "sleep_minutes": 420.0,
            "awake_minutes": 60.0,
            "quality": "good",
            "stages": {
                "awake_minutes": 60.0,
                "light_minutes": 200.0,
                "deep_minutes": 100.0,
                "rem_minutes": 120.0,
            },
            "interruption_count": 2,
        },
    ),
    (
        "daily_activity",
        {
            "activity_date": "2026-01-02",
            "steps": 1000,
            "distance_kilometers": 1.2,
            "active_minutes": 20.0,
            "active_calories_kcal": 100.0,
        },
    ),
    (
        "workout",
        {
            "period": {
                "start": "2026-01-03T08:00:00+05:30",
                "end": "2026-01-03T09:00:00+05:30",
            },
            "workout_type": "running",
            "distance_kilometers": 5.0,
            "active_calories_kcal": 300.0,
            "perceived_exertion": 5,
            "average_heart_rate_bpm": 140.0,
        },
    ),
    (
        "hydration",
        {
            "volume_milliliters": 250.0,
            "beverage_type": "water",
            "caffeine_milligrams": 0.0,
        },
    ),
    (
        "meal",
        {
            "meal_type": "breakfast",
            "nutrition": {
                "calories_kcal": 400.0,
                "protein_grams": 20.0,
                "carbohydrates_grams": 50.0,
                "fat_grams": 12.0,
                "fibre_grams": 8.0,
            },
            "name": "Oats",
        },
    ),
    (
        "daily_nutrition",
        {
            "nutrition_date": "2026-01-06",
            "nutrition": {"calories_kcal": 1800.0},
            "meal_count": 3,
        },
    ),
    (
        "body_measurement",
        {
            "weight_kilograms": 70.0,
            "height_meters": 1.75,
            "body_fat_percent": 20.0,
            "waist_circumference_centimeters": 80.0,
        },
    ),
    (
        "subjective_check_in",
        {
            "mood_score": 4,
            "energy_score": 4,
            "stress_score": 2,
            "motivation_score": 4,
            "mood_category": "high",
            "tags": ["calm", "focused"],
        },
    ),
    (
        "menstrual_bleeding",
        {
            "flow": "light",
            "symptoms": [{"symptom": "cramps", "intensity": "mild"}],
        },
    ),
    ("menstrual_cycle", {"start_date": "2026-01-10", "end_date": "2026-01-14"}),
)


def record_payload(index: int) -> dict[str, object]:
    record_type, data = RECORD_SAMPLES[index]
    return {
        "record_type": record_type,
        "metadata": {
            "recorded_at": f"2026-01-{index + 1:02d}T12:00:00+05:30",
            "source": "manual",
            "notes": "  user supplied note  ",
        },
        "data": deepcopy(data),
    }


def test_profile_onboarding_read_update_cardinality_and_transport_privacy(tmp_path: Path) -> None:
    app = create_app(settings(tmp_path / "profile.db"))
    assert request(app, "GET", "/api/v1/profile").status_code == 401
    assert request(app, "POST", "/api/v1/profile", json={"time_zone": "UTC"}).status_code == 401
    headers = authorize(app, "profile@example.com")
    malformed = request(
        app,
        "GET",
        "/api/v1/profile",
        headers={"Authorization": "Bearer malformed"},
    )
    assert (malformed.status_code, malformed.json()["error"]["code"]) == (
        401,
        "invalid_access_token",
    )
    missing = request(app, "GET", "/api/v1/profile", headers=headers)
    assert (missing.status_code, missing.json()["error"]["code"]) == (
        404,
        "profile_not_configured",
    )

    created = create_profile(app, headers)
    profile_id = created["profile_id"]
    UUID(str(profile_id))
    assert set(created) == {
        "profile_id",
        "time_zone",
        "display_name",
        "measurement_system",
        "week_start",
        "tracked_domains",
    }
    assert "user_id" not in str(created) and "owner" not in str(created)
    assert request(app, "GET", "/api/v1/auth/me", headers=headers).json()["profile_ids"] == [
        profile_id
    ]
    assert request(app, "GET", "/api/v1/profile", headers=headers).json() == created
    duplicate = request(app, "POST", "/api/v1/profile", headers=headers, json={"time_zone": "UTC"})
    assert (duplicate.status_code, duplicate.json()["error"]["code"]) == (
        409,
        "profile_already_exists",
    )

    updated = request(
        app,
        "PUT",
        "/api/v1/profile",
        headers=headers,
        json={
            "time_zone": "UTC",
            "display_name": "Updated",
            "measurement_system": "imperial",
            "week_start": "sunday",
            "tracked_domains": ["body_measurements"],
        },
    )
    assert updated.status_code == 200
    assert updated.json()["profile_id"] == profile_id
    assert updated.json()["display_name"] == "Updated"
    forbidden = request(
        app,
        "PUT",
        "/api/v1/profile",
        headers=headers,
        json={"time_zone": "UTC", "profile_id": profile_id},
    )
    assert forbidden.status_code == 422
    invalid = request(
        app, "PUT", "/api/v1/profile", headers=headers, json={"time_zone": "not-a-zone"}
    )
    assert (invalid.status_code, invalid.json()["error"]["code"]) == (
        422,
        "domain_validation_error",
    )
    assert request(app, "PUT", "/api/v1/profile", json={"time_zone": "UTC"}).status_code == 401


def test_every_record_type_round_trips_and_filters_use_repository_semantics(tmp_path: Path) -> None:
    app = create_app(settings(tmp_path / "records.db"))
    assert request(app, "POST", "/api/v1/records", json=record_payload(3)).status_code == 401
    headers = authorize(app, "records@example.com")
    no_profile = request(app, "GET", "/api/v1/records", headers=headers)
    assert no_profile.json()["error"]["code"] == "profile_not_configured"
    create_profile(app, headers)
    assert request(app, "GET", "/api/v1/records", headers=headers).json() == []

    created: list[dict[str, object]] = []
    for index, (record_type, _) in enumerate(RECORD_SAMPLES):
        response = request(
            app,
            "POST",
            "/api/v1/records",
            headers=headers,
            json=record_payload(index),
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["record_type"] == record_type
        assert set(body) == {"record_type", "metadata", "data"}
        serialized = str(body)
        assert not any(
            field in serialized
            for field in ("profile_id", "user_id", "schema_version", "payload_type")
        )
        assert set(body["metadata"]) == {"record_id", "recorded_at", "source", "notes"}
        UUID(body["metadata"]["record_id"])
        assert body["metadata"]["notes"] == "user supplied note"
        created.append(body)

    listed = request(app, "GET", "/api/v1/records", headers=headers)
    assert listed.status_code == 200
    assert [item["record_type"] for item in listed.json()] == [
        item["record_type"] for item in created
    ]
    for item in created:
        retrieved = request(
            app,
            "GET",
            f"/api/v1/records/{item['metadata']['record_id']}",
            headers=headers,
        )
        assert retrieved.status_code == 200
        assert retrieved.json() == item

    hydration = request(app, "GET", "/api/v1/records?record_type=hydration", headers=headers).json()
    assert [item["record_type"] for item in hydration] == ["hydration"]
    ranged = request(
        app,
        "GET",
        "/api/v1/records?start=2026-01-02T12:00:00%2B05:30&end=2026-01-04T12:00:00%2B05:30",
        headers=headers,
    ).json()
    assert [item["record_type"] for item in ranged] == ["daily_activity", "workout"]
    combined = request(
        app,
        "GET",
        "/api/v1/records?record_type=workout&start=2026-01-03T12:00:00%2B05:30"
        "&end=2026-01-04T12:00:00%2B05:30",
        headers=headers,
    ).json()
    assert [item["record_type"] for item in combined] == ["workout"]
    incomplete = request(
        app,
        "GET",
        "/api/v1/records?start=2026-01-03T12:00:00%2B05:30",
        headers=headers,
    )
    assert (incomplete.status_code, incomplete.json()["error"]["code"]) == (
        400,
        "application_validation_error",
    )


@pytest.mark.parametrize("index", range(len(RECORD_SAMPLES)))
def test_each_record_discriminator_rejects_an_invalid_payload(tmp_path: Path, index: int) -> None:
    app = create_app(settings(tmp_path / f"invalid-{index}.db"))
    headers = authorize(app, f"invalid-{index}@example.com")
    create_profile(app, headers)
    payload = record_payload(index)
    payload["data"]["unsupported_field"] = True  # type: ignore[index]
    response = request(app, "POST", "/api/v1/records", headers=headers, json=payload)
    assert (response.status_code, response.json()["error"]["code"]) == (
        422,
        "request_validation_error",
    )


@pytest.mark.parametrize(
    ("payload", "expected_code"),
    [
        ({"record_type": "unknown", "metadata": {}, "data": {}}, "request_validation_error"),
        (
            {
                **record_payload(3),
                "profile_id": "00000000-0000-4000-8000-000000000001",
            },
            "request_validation_error",
        ),
        (
            {
                **record_payload(3),
                "metadata": {
                    "recorded_at": "2026-01-01T12:00:00",
                    "source": "manual",
                },
            },
            "domain_validation_error",
        ),
        (
            {
                **record_payload(3),
                "data": {"volume_milliliters": "250"},
            },
            "request_validation_error",
        ),
    ],
)
def test_record_validation_is_safe_and_ownership_fields_are_rejected(
    tmp_path: Path, payload: dict[str, object], expected_code: str
) -> None:
    app = create_app(settings(tmp_path / "invalid.db"))
    headers = authorize(app, "invalid@example.com")
    create_profile(app, headers)
    response = request(app, "POST", "/api/v1/records", headers=headers, json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == expected_code
    assert str(tmp_path) not in response.text


def test_missing_cross_user_record_isolation_and_restart_durability(tmp_path: Path) -> None:
    database = tmp_path / "durable.db"
    app = create_app(settings(database))
    user_a = authorize(app, "a@example.com")
    user_b = authorize(app, "b@example.com")
    profile_a = create_profile(app, user_a, "A")
    profile_b = create_profile(app, user_b, "B")
    record_a = request(
        app, "POST", "/api/v1/records", headers=user_a, json=record_payload(3)
    ).json()
    record_b = request(
        app, "POST", "/api/v1/records", headers=user_b, json=record_payload(4)
    ).json()

    assert request(app, "GET", "/api/v1/profile", headers=user_a).json() == profile_a
    assert request(app, "GET", "/api/v1/profile", headers=user_b).json() == profile_b
    updated_a = request(
        app,
        "PUT",
        "/api/v1/profile",
        headers=user_a,
        json={"time_zone": "UTC", "display_name": "A updated"},
    ).json()
    assert updated_a["profile_id"] == profile_a["profile_id"]
    assert request(app, "GET", "/api/v1/profile", headers=user_b).json() == profile_b
    assert [
        item["metadata"]["record_id"]
        for item in request(app, "GET", "/api/v1/records", headers=user_a).json()
    ] == [record_a["metadata"]["record_id"]]
    cross = request(
        app,
        "GET",
        f"/api/v1/records/{record_b['metadata']['record_id']}",
        headers=user_a,
    )
    missing = request(
        app,
        "GET",
        "/api/v1/records/00000000-0000-4000-8000-000000000099",
        headers=user_a,
    )
    assert {
        (cross.status_code, cross.json()["error"]["code"]),
        (
            missing.status_code,
            missing.json()["error"]["code"],
        ),
    } == {(404, "wellness_record_not_found")}
    malformed = request(app, "GET", "/api/v1/records/not-a-uuid", headers=user_a)
    assert (malformed.status_code, malformed.json()["error"]["code"]) == (
        422,
        "request_validation_error",
    )

    restarted = create_app(settings(database))
    token = request(
        restarted,
        "POST",
        "/api/v1/auth/login",
        json={"email": "a@example.com", "password": PASSWORD},
    ).json()["access_token"]
    restarted_a = {"Authorization": f"Bearer {token}"}
    assert request(restarted, "GET", "/api/v1/profile", headers=restarted_a).json() == updated_a
    assert (
        request(
            restarted,
            "GET",
            f"/api/v1/records/{record_a['metadata']['record_id']}",
            headers=restarted_a,
        ).json()
        == record_a
    )


def test_openapi_record_union_is_exhaustive_protected_and_custom_prefix_works(
    tmp_path: Path,
) -> None:
    app = create_app(settings(tmp_path / "openapi.db", api_prefix="/service/v1"))
    schema = app.openapi()
    protected = {("/service/v1/profile", method) for method in ("post", "get", "put")} | {
        ("/service/v1/records", "post"),
        ("/service/v1/records", "get"),
        ("/service/v1/records/{record_id}", "get"),
    }
    assert set(schema["components"]["securitySchemes"]) == {"BearerAuth"}
    assert all(
        schema["paths"][path][method]["security"] == [{"BearerAuth": []}]
        for path, method in protected
    )
    discriminator = schema["paths"]["/service/v1/records"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]["discriminator"]
    assert set(discriminator["mapping"]) == {record_type for record_type, _ in RECORD_SAMPLES}
    paths = set(schema["paths"])
    assert not any(term in path for path in paths for term in ("/baselines", "/trends"))
    assert not any("refresh" in path for path in paths)
