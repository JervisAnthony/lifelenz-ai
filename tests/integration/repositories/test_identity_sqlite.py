import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from lifelenz.domain import ProfileId
from lifelenz.identity import EmailAddress, UserAccount, UserId
from lifelenz.repositories import (
    DuplicateEntityError,
    EntityNotFoundError,
    SQLiteProfileOwnershipRepository,
    SQLiteUserAccountRepository,
)


def account(email: str = "user@example.com") -> UserAccount:
    return UserAccount(UserId.new(), EmailAddress.from_raw(email), "$argon2id$synthetic", True)


def test_account_round_trip_update_restart_and_email_lookup(tmp_path: Path) -> None:
    path = tmp_path / "identity.db"
    repository = SQLiteUserAccountRepository(path)
    original = account("User@Example.com")
    repository.save(original)
    assert repository.get(original.user_id) == original
    assert repository.get_by_email(EmailAddress.from_raw("USER@example.com")) == original
    assert repository.exists(original.user_id) is True
    assert repository.exists_by_email(original.email) is True
    updated = replace(original, password_hash="new-private-hash", is_active=False)
    repository.save(updated)
    assert SQLiteUserAccountRepository(path).get(original.user_id) == updated


def test_account_email_uniqueness_and_missing_behavior(tmp_path: Path) -> None:
    repository = SQLiteUserAccountRepository(tmp_path / "accounts.db")
    first = account()
    repository.save(first)
    with pytest.raises(DuplicateEntityError):
        repository.save(account(" USER@example.com "))
    with pytest.raises(EntityNotFoundError):
        repository.get(UserId.new())
    with pytest.raises(EntityNotFoundError):
        repository.get_by_email(EmailAddress.from_raw("missing@example.com"))


def test_account_repository_rejects_wrong_types_before_sql(tmp_path: Path) -> None:
    repository = SQLiteUserAccountRepository(tmp_path / "strict.db")
    with pytest.raises(TypeError):
        repository.save({})  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        repository.get(ProfileId.generate())  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        repository.get_by_email("user@example.com")  # type: ignore[arg-type]


def test_ownership_upsert_order_remove_and_no_cascade(tmp_path: Path) -> None:
    path = tmp_path / "ownership.db"
    repository = SQLiteProfileOwnershipRepository(path)
    first_user, second_user = UserId.new(), UserId.new()
    profiles = (
        ProfileId("00000000-0000-4000-8000-000000000002"),
        ProfileId("00000000-0000-4000-8000-000000000001"),
    )
    repository.assign(first_user, profiles[0])
    repository.assign(first_user, profiles[1])
    assert repository.list_for_user(first_user) == (profiles[1], profiles[0])
    repository.assign(second_user, profiles[0])
    assert repository.get_owner(profiles[0]) == second_user
    assert repository.is_owner(first_user, profiles[0]) is False
    repository.remove(profiles[0])
    with pytest.raises(EntityNotFoundError):
        repository.get_owner(profiles[0])
    connection = sqlite3.connect(path)
    try:
        assert connection.execute("SELECT COUNT(*) FROM user_accounts").fetchone()[0] == 0
    finally:
        connection.close()
