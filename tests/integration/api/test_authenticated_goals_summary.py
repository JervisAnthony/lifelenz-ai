import asyncio
from pathlib import Path
from uuid import UUID

import httpx

from lifelenz.api import ApiSettings, create_app
from lifelenz.domain import GoalDirection, GoalStatus, MetricIdentifier
from lifelenz.domain.taxonomy import DEFAULT_UNIT_BY_METRIC

SECRET = "authenticated-goal-summary-test-secret-at-least-32-bytes"
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
        json={"time_zone": "UTC"},
    )
    assert response.status_code == 201


def goal_payload(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "target": {"metric": "water_intake", "value": 2000, "unit": "milliliters"},
        "direction": "at_least",
        "status": "active",
        "start_date": "2026-01-01",
        "target_date": "2026-12-31",
        "title": "Daily water",
        "description": "Structured user target",
    }
    payload.update(changes)
    return payload


def create_goal(app: object, headers: dict[str, str], **changes: object) -> dict[str, object]:
    response = request(
        app,
        "POST",
        "/api/v1/goals",
        headers=headers,
        json=goal_payload(**changes),
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_hydration(
    app: object,
    headers: dict[str, str],
    *,
    day: int,
    volume: float,
) -> None:
    response = request(
        app,
        "POST",
        "/api/v1/records",
        headers=headers,
        json={
            "record_type": "hydration",
            "metadata": {
                "recorded_at": f"2026-01-{day:02d}T08:00:00+05:30",
                "source": "manual",
            },
            "data": {"volume_milliliters": volume},
        },
    )
    assert response.status_code == 201, response.text


def create_body_measurement(app: object, headers: dict[str, str]) -> None:
    response = request(
        app,
        "POST",
        "/api/v1/records",
        headers=headers,
        json={
            "record_type": "body_measurement",
            "metadata": {
                "recorded_at": "2026-01-02T12:00:00+05:30",
                "source": "manual",
            },
            "data": {"weight_kilograms": 70.0},
        },
    )
    assert response.status_code == 201, response.text


def test_goal_lifecycle_validation_delete_and_transport_privacy(tmp_path: Path) -> None:
    app = create_app(settings(tmp_path / "goals.db"))
    assert request(app, "GET", "/api/v1/goals").status_code == 401
    assert request(app, "POST", "/api/v1/goals", json=goal_payload()).status_code == 401
    headers = authorize(app, "goals@example.com")
    invalid_token = request(
        app,
        "GET",
        "/api/v1/goals",
        headers={"Authorization": "Bearer invalid"},
    )
    assert (invalid_token.status_code, invalid_token.json()["error"]["code"]) == (
        401,
        "invalid_access_token",
    )
    no_profile = request(app, "GET", "/api/v1/goals", headers=headers)
    assert (no_profile.status_code, no_profile.json()["error"]["code"]) == (
        404,
        "profile_not_configured",
    )
    create_profile(app, headers)
    assert request(app, "GET", "/api/v1/goals", headers=headers).json() == []

    forbidden = goal_payload(profile_id="00000000-0000-4000-8000-000000000001")
    assert request(app, "POST", "/api/v1/goals", headers=headers, json=forbidden).status_code == 422
    created = create_goal(app, headers)
    UUID(str(created["goal_id"]))
    assert set(created) == {
        "goal_id",
        "target",
        "direction",
        "status",
        "start_date",
        "target_date",
        "title",
        "description",
    }
    assert not any(field in str(created) for field in ("profile_id", "user_id", "owner_id"))
    assert request(app, "GET", "/api/v1/goals", headers=headers).json() == [created]
    goal_id = created["goal_id"]
    assert request(app, "GET", f"/api/v1/goals/{goal_id}", headers=headers).json() == created

    updated = request(
        app,
        "PUT",
        f"/api/v1/goals/{goal_id}",
        headers=headers,
        json=goal_payload(status="paused", title="Updated"),
    )
    assert updated.status_code == 200
    assert updated.json()["goal_id"] == goal_id
    assert updated.json()["status"] == "paused"
    assert updated.json()["title"] == "Updated"
    invalid_unit = request(
        app,
        "POST",
        "/api/v1/goals",
        headers=headers,
        json=goal_payload(target={"metric": "steps", "value": 1000, "unit": "milliliters"}),
    )
    assert (invalid_unit.status_code, invalid_unit.json()["error"]["code"]) == (
        422,
        "domain_validation_error",
    )
    missing = request(
        app,
        "GET",
        "/api/v1/goals/00000000-0000-4000-8000-000000000099",
        headers=headers,
    )
    malformed = request(app, "GET", "/api/v1/goals/not-a-uuid", headers=headers)
    assert (missing.status_code, missing.json()["error"]["code"]) == (404, "goal_not_found")
    assert (malformed.status_code, malformed.json()["error"]["code"]) == (
        422,
        "request_validation_error",
    )
    deleted = request(app, "DELETE", f"/api/v1/goals/{goal_id}", headers=headers)
    assert deleted.status_code == 204 and deleted.content == b""
    assert request(app, "GET", f"/api/v1/goals/{goal_id}", headers=headers).status_code == 404


def test_every_goal_direction_and_status_maps_through_api(tmp_path: Path) -> None:
    app = create_app(settings(tmp_path / "goal-enums.db"))
    headers = authorize(app, "goal-enums@example.com")
    create_profile(app, headers)
    observed = set()
    for direction in GoalDirection:
        for status in GoalStatus:
            created = create_goal(
                app,
                headers,
                direction=direction.value,
                status=status.value,
                title=f"{direction.value}-{status.value}",
            )
            observed.add((created["direction"], created["status"]))
    assert observed == {
        (direction.value, status.value) for direction in GoalDirection for status in GoalStatus
    }
    for metric, unit in DEFAULT_UNIT_BY_METRIC.items():
        created = create_goal(
            app,
            headers,
            target={"metric": metric.value, "value": 1, "unit": unit.value},
            title=metric.value,
        )
        assert created["target"] == {
            "metric": metric.value,
            "value": 1,
            "unit": unit.value,
        }
    listed_ids = [
        item["goal_id"] for item in request(app, "GET", "/api/v1/goals", headers=headers).json()
    ]
    assert listed_ids == sorted(listed_ids)


def test_goal_cross_user_operations_do_not_enumerate_resources(tmp_path: Path) -> None:
    app = create_app(settings(tmp_path / "goal-isolation.db"))
    user_a = authorize(app, "goal-a@example.com")
    user_b = authorize(app, "goal-b@example.com")
    create_profile(app, user_a)
    create_profile(app, user_b)
    goal_a = create_goal(app, user_a, title="A")
    goal_b = create_goal(app, user_b, title="B")

    assert [
        goal["goal_id"] for goal in request(app, "GET", "/api/v1/goals", headers=user_a).json()
    ] == [goal_a["goal_id"]]
    assert [
        goal["goal_id"] for goal in request(app, "GET", "/api/v1/goals", headers=user_b).json()
    ] == [goal_b["goal_id"]]
    for method in ("GET", "PUT", "DELETE"):
        response = request(
            app,
            method,
            f"/api/v1/goals/{goal_b['goal_id']}",
            headers=user_a,
            **({"json": goal_payload(title="intrusion")} if method == "PUT" else {}),
        )
        assert (response.status_code, response.json()["error"]["code"]) == (
            404,
            "goal_not_found",
        )
    symmetric = request(app, "GET", f"/api/v1/goals/{goal_a['goal_id']}", headers=user_b)
    assert (symmetric.status_code, symmetric.json()["error"]["code"]) == (
        404,
        "goal_not_found",
    )


def test_summary_baseline_trend_metric_and_time_filtering(tmp_path: Path) -> None:
    app = create_app(settings(tmp_path / "summary.db"))
    assert request(app, "GET", "/api/v1/summary").status_code == 401
    headers = authorize(app, "summary@example.com")
    no_profile = request(app, "GET", "/api/v1/summary", headers=headers)
    assert no_profile.json()["error"]["code"] == "profile_not_configured"
    create_profile(app, headers)
    unavailable = request(app, "GET", "/api/v1/summary", headers=headers)
    assert (unavailable.status_code, unavailable.json()["error"]["code"]) == (
        404,
        "wellness_summary_unavailable",
    )

    create_hydration(app, headers, day=1, volume=250.0)
    one = request(app, "GET", "/api/v1/summary?metric=water_intake", headers=headers)
    assert one.status_code == 200
    assert set(one.json()) == {"metrics", "time_range", "generated_from_record_count"}
    metric = one.json()["metrics"][0]
    assert metric["metric"] == "water_intake"
    assert metric["baseline"]["sample_count"] == 1
    assert metric["baseline"]["mean"] == 250.0
    assert metric["baseline"]["median"] == 250.0
    assert metric["baseline"]["minimum"] == 250.0
    assert metric["baseline"]["maximum"] == 250.0
    assert metric["baseline"]["population_standard_deviation"] == 0.0
    assert metric["trend"] is None
    assert not any(field in str(one.json()) for field in ("profile_id", "user_id", "record_id"))

    create_hydration(app, headers, day=2, volume=500.0)
    two = request(app, "GET", "/api/v1/summary?metric=water_intake", headers=headers).json()
    metric = two["metrics"][0]
    assert metric["baseline"]["mean"] == 375.0
    assert metric["baseline"]["population_standard_deviation"] == 125.0
    assert metric["trend"] == {
        "sample_count": 2,
        "first_value": 250.0,
        "last_value": 500.0,
        "absolute_change": 250.0,
        "percentage_change": 100.0,
        "slope_per_day": 250.0,
        "direction": "increasing",
        "stability_tolerance": 0.0,
        "first_observed_at": "2026-01-01T08:00:00+05:30",
        "last_observed_at": "2026-01-02T08:00:00+05:30",
        "time_range": None,
    }
    create_body_measurement(app, headers)
    selected = request(
        app,
        "GET",
        "/api/v1/summary?metric=weight&metric=water_intake",
        headers=headers,
    ).json()
    assert [metric["metric"] for metric in selected["metrics"]] == ["water_intake", "weight"]
    ranged = request(
        app,
        "GET",
        "/api/v1/summary?metric=water_intake&start=2026-01-02T08:00:00%2B05:30"
        "&end=2026-01-03T08:00:00%2B05:30",
        headers=headers,
    ).json()
    assert ranged["metrics"][0]["baseline"]["sample_count"] == 1
    assert ranged["metrics"][0]["baseline"]["mean"] == 500.0
    assert ranged["metrics"][0]["trend"] is None


def test_summary_validation_metric_exhaustiveness_and_openapi(tmp_path: Path) -> None:
    app = create_app(settings(tmp_path / "summary-validation.db", api_prefix="/service/v1"))
    schema = app.openapi()
    metric_schema = schema["components"]["schemas"]["MetricIdentifier"]
    assert set(metric_schema["enum"]) == {metric.value for metric in MetricIdentifier}
    protected = {
        ("/service/v1/goals", "post"),
        ("/service/v1/goals", "get"),
        ("/service/v1/goals/{goal_id}", "get"),
        ("/service/v1/goals/{goal_id}", "put"),
        ("/service/v1/goals/{goal_id}", "delete"),
        ("/service/v1/summary", "get"),
    }
    assert set(schema["components"]["securitySchemes"]) == {"BearerAuth"}
    assert all(
        schema["paths"][path][method]["security"] == [{"BearerAuth": []}]
        for path, method in protected
    )

    default_app = create_app(settings(tmp_path / "validation.db"))
    headers = authorize(default_app, "validation@example.com")
    create_profile(default_app, headers)
    create_hydration(default_app, headers, day=1, volume=250.0)
    cases = (
        ("?metric=unsupported", 422, "request_validation_error"),
        ("?metric=steps", 404, "wellness_summary_unavailable"),
        ("?start=2026-01-01T00:00:00", 400, "application_validation_error"),
        (
            "?start=2026-01-01T00:00:00&end=2026-01-02T00:00:00",
            422,
            "domain_validation_error",
        ),
        (
            "?metric=water_intake&metric=water_intake",
            400,
            "application_validation_error",
        ),
    )
    for query, status_code, code in cases:
        response = request(default_app, "GET", "/api/v1/summary" + query, headers=headers)
        assert (response.status_code, response.json()["error"]["code"]) == (
            status_code,
            code,
        )


def test_summary_cross_user_isolation_and_restart_durability(tmp_path: Path) -> None:
    database = tmp_path / "durable.db"
    app = create_app(settings(database))
    user_a = authorize(app, "durable-a@example.com")
    user_b = authorize(app, "durable-b@example.com")
    create_profile(app, user_a)
    create_profile(app, user_b)
    goal_a = create_goal(app, user_a, title="Durable A")
    create_hydration(app, user_a, day=1, volume=100.0)
    create_hydration(app, user_a, day=2, volume=200.0)
    create_hydration(app, user_b, day=1, volume=1000.0)
    create_hydration(app, user_b, day=2, volume=2000.0)

    summary_a = request(app, "GET", "/api/v1/summary", headers=user_a).json()
    summary_b = request(app, "GET", "/api/v1/summary", headers=user_b).json()
    assert summary_a["metrics"][0]["baseline"]["mean"] == 150.0
    assert summary_b["metrics"][0]["baseline"]["mean"] == 1500.0

    restarted = create_app(settings(database))
    token = request(
        restarted,
        "POST",
        "/api/v1/auth/login",
        json={"email": "durable-a@example.com", "password": PASSWORD},
    ).json()["access_token"]
    restarted_a = {"Authorization": f"Bearer {token}"}
    assert (
        request(
            restarted,
            "GET",
            f"/api/v1/goals/{goal_a['goal_id']}",
            headers=restarted_a,
        ).json()
        == goal_a
    )
    assert request(restarted, "GET", "/api/v1/summary", headers=restarted_a).json() == summary_a
