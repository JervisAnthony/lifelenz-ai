"""Explicit construction for the version-one API router."""

from fastapi import APIRouter

from lifelenz.api.routes.auth import create_auth_router
from lifelenz.api.routes.system import create_system_router


def create_v1_router() -> APIRouter:
    """Return a fresh router containing version-one system and authentication endpoints."""
    router = create_system_router(operation_prefix="v1", include_metadata_slash=False)
    router.include_router(create_auth_router())
    return router
