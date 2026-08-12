"""Explicit construction for the version-one API router."""

from fastapi import APIRouter

from lifelenz.api.routes.auth import create_auth_router
from lifelenz.api.routes.profile import create_profile_router
from lifelenz.api.routes.records import create_records_router
from lifelenz.api.routes.system import create_system_router


def create_v1_router() -> APIRouter:
    """Return a fresh router containing the complete version-one API surface."""
    router = create_system_router(operation_prefix="v1", include_metadata_slash=False)
    # System routes already carry their own tag; included resource routers should
    # retain only their resource-specific tags.
    router.tags.clear()
    router.include_router(create_auth_router())
    router.include_router(create_profile_router())
    router.include_router(create_records_router())
    return router
