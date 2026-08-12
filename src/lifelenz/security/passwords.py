"""Argon2 password hashing through pwdlib's recommended configuration."""

from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

from lifelenz.security.exceptions import PasswordHashError

_MIN_PASSWORD_LENGTH = 12
_MAX_PASSWORD_LENGTH = 256


class Argon2PasswordHasher:
    """Hash and verify bounded passphrases without exposing pwdlib internals."""

    __slots__ = ("__password_hash",)

    def __init__(self) -> None:
        self.__password_hash = PasswordHash.recommended()

    @staticmethod
    def _validate_password(password: object) -> str:
        if type(password) is not str:
            raise TypeError("password must be a string")
        if not _MIN_PASSWORD_LENGTH <= len(password) <= _MAX_PASSWORD_LENGTH:
            raise ValueError("password length must be between 12 and 256 characters")
        return password

    def hash_password(self, password: str) -> str:
        """Return a freshly salted Argon2 hash for a valid passphrase."""
        return self.__password_hash.hash(self._validate_password(password))

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Return false for a mismatch and fail safely for a corrupt stored hash."""
        validated_password = self._validate_password(password)
        if type(password_hash) is not str or not password_hash:
            raise PasswordHashError("stored password hash is invalid")
        try:
            return self.__password_hash.verify(validated_password, password_hash)
        except (UnknownHashError, ValueError) as error:
            raise PasswordHashError("stored password hash is invalid") from error
