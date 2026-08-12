import pytest

from lifelenz.security import Argon2PasswordHasher, PasswordHashError


def test_argon2_hashes_are_salted_and_verify_without_plaintext() -> None:
    hasher = Argon2PasswordHasher()
    first = hasher.hash_password("correct horse battery staple")
    second = hasher.hash_password("correct horse battery staple")
    assert first.startswith("$argon2")
    assert first != second
    assert "correct horse" not in first
    assert hasher.verify_password("correct horse battery staple", first) is True
    assert hasher.verify_password("incorrect horse battery staple", first) is False


@pytest.mark.parametrize("password", ["", "short", "x" * 257, None, 12])
def test_password_policy_is_strict(password: object) -> None:
    with pytest.raises((TypeError, ValueError)) as caught:
        Argon2PasswordHasher().hash_password(password)  # type: ignore[arg-type]
    assert str(password) not in str(caught.value) if password else True


def test_corrupt_hash_is_not_treated_as_normal_mismatch() -> None:
    with pytest.raises(PasswordHashError) as caught:
        Argon2PasswordHasher().verify_password("valid passphrase here", "not-a-password-hash")
    assert "not-a-password-hash" not in str(caught.value)
