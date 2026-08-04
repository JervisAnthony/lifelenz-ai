"""Request-local correlation identifier middleware."""

from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import FastAPI, Request, Response

REQUEST_ID_HEADER = "X-Request-ID"
_MAX_REQUEST_ID_LENGTH = 128


def _valid_request_id(value: str | None) -> bool:
    return bool(
        value
        and value == value.strip()
        and len(value) <= _MAX_REQUEST_ID_LENGTH
        and all(33 <= ord(character) <= 126 for character in value)
    )


def resolve_request_id(value: str | None) -> str:
    """Preserve a conservative ASCII token or generate a UUID4 identifier."""
    return value if _valid_request_id(value) else str(uuid4())


async def request_id_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Attach one request-local correlation identifier to state and the response."""
    request_id = resolve_request_id(request.headers.get(REQUEST_ID_HEADER))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers[REQUEST_ID_HEADER] = request_id
    return response


def register_request_id_middleware(app: FastAPI) -> None:
    """Register correlation middleware on one application instance."""
    app.middleware("http")(request_id_middleware)
