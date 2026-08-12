from dataclasses import FrozenInstanceError
from uuid import UUID

import pytest

import lifelenz.identity
from lifelenz.identity import EmailAddress, UserAccount, UserId


def test_user_id_is_strict_immutable_uuid_identity() -> None:
    user_id = UserId.new()
    assert user_id.value.version == 4
    assert str(user_id) == str(user_id.value)
    assert hash(user_id)
    assert not hasattr(user_id, "__dict__")
    with pytest.raises((FrozenInstanceError, AttributeError)):
        user_id.value = UUID(int=0)  # type: ignore[misc]
    with pytest.raises(TypeError):
        UserId(str(user_id.value))  # type: ignore[arg-type]


@pytest.mark.parametrize("raw", ["Tony@Example.com", "tony@example.com", " TONY@example.com "])
def test_email_normalizes_to_one_canonical_identity(raw: str) -> None:
    assert EmailAddress.from_raw(raw) == EmailAddress("tony@example.com")


@pytest.mark.parametrize(
    "raw",
    ["", "  ", "missing", "a@@example.com", "@example.com", "a@", "a b@example.com", "a@-bad.com"],
)
def test_email_rejects_malformed_values(raw: str) -> None:
    with pytest.raises(ValueError):
        EmailAddress.from_raw(raw)


def test_account_hides_hash_and_rejects_wrong_boundary_types() -> None:
    account = UserAccount(
        UserId.new(), EmailAddress.from_raw("a@example.com"), "private-hash", True
    )
    assert "private-hash" not in repr(account)
    assert hash(account)
    with pytest.raises(TypeError):
        UserAccount(account.user_id, account.email, "hash", 1)  # type: ignore[arg-type]


def test_identity_public_api_is_exact() -> None:
    assert lifelenz.identity.__all__ == ["EmailAddress", "UserAccount", "UserId"]
