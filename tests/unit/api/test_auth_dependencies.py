import asyncio
from pathlib import Path

import httpx

from lifelenz.api import ApiSettings, create_app

SECRET = "dependency-test-secret-material-at-least-32-bytes"


def get(app: object, headers: dict[str, str] | None = None) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)  # type: ignore[arg-type]
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/api/v1/auth/me", headers=headers)

    return asyncio.run(send())


def test_missing_malformed_and_wrong_scheme_credentials_use_safe_401(tmp_path: Path) -> None:
    app = create_app(ApiSettings("LifeLenz-AI", "0.1.0", "test", tmp_path / "api.db", SECRET))
    for headers in (None, {"Authorization": "Basic abc"}, {"Authorization": "Bearer not.jwt"}):
        response = get(app, headers)
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"
        assert response.json()["error"]["code"] == "invalid_access_token"
        assert "jwt" not in response.text.casefold()
