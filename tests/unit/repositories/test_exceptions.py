"""Tests for storage-independent repository exceptions."""

import pytest

from lifelenz.repositories import (
    DuplicateEntityError,
    EntityNotFoundError,
    RepositoryError,
)


def test_repository_error_derives_from_exception() -> None:
    assert issubclass(RepositoryError, Exception)


@pytest.mark.parametrize("exception_type", [EntityNotFoundError, DuplicateEntityError])
def test_specific_errors_derive_from_repository_error(
    exception_type: type[RepositoryError],
) -> None:
    assert issubclass(exception_type, RepositoryError)


@pytest.mark.parametrize(
    "exception_type", [RepositoryError, EntityNotFoundError, DuplicateEntityError]
)
def test_custom_messages_are_preserved(exception_type: type[RepositoryError]) -> None:
    error = exception_type("wellness goal goal-123")

    assert str(error) == "wellness goal goal-123"


@pytest.mark.parametrize("exception_type", [EntityNotFoundError, DuplicateEntityError])
def test_specific_errors_are_catchable_through_base_type(
    exception_type: type[RepositoryError],
) -> None:
    with pytest.raises(RepositoryError, match="entity-123"):
        raise exception_type("entity-123")


@pytest.mark.parametrize(
    "exception_type", [RepositoryError, EntityNotFoundError, DuplicateEntityError]
)
def test_exceptions_require_no_provider_specific_attributes(
    exception_type: type[RepositoryError],
) -> None:
    error = exception_type("entity-123")

    assert not hasattr(error, "http_status")
    assert not hasattr(error, "provider")
    assert not hasattr(error, "retry_after")
