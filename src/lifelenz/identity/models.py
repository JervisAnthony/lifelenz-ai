"""Immutable account identity values with strict construction boundaries."""

from dataclasses import dataclass, field
from typing import Self
from unicodedata import category
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class UserId:
    """A semantically distinct UUID-backed account identifier."""

    value: UUID

    def __post_init__(self) -> None:
        if type(self.value) is not UUID:
            raise TypeError("user identifier value must be a UUID")

    @classmethod
    def new(cls) -> Self:
        """Generate a new random UUID4 account identifier."""
        return cls(uuid4())

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True)
class EmailAddress:
    """A canonical case-folded email address used as account identity."""

    value: str

    def __post_init__(self) -> None:
        if type(self.value) is not str:
            raise TypeError("email address value must be a string")
        if self.value != self.value.strip().casefold():
            raise ValueError("email address must be in canonical form")
        if not self.value or len(self.value) > 254:
            raise ValueError("email address length is invalid")
        if any(
            character.isspace() or category(character).startswith("C") for character in self.value
        ):
            raise ValueError("email address contains an invalid character")
        if self.value.count("@") != 1:
            raise ValueError("email address must contain one separator")
        local, domain = self.value.split("@")
        if not local or not domain or len(local) > 64:
            raise ValueError("email address structure is invalid")
        if local.startswith(".") or local.endswith(".") or ".." in local:
            raise ValueError("email address local part is invalid")
        labels = domain.split(".")
        if any(not label or label.startswith("-") or label.endswith("-") for label in labels):
            raise ValueError("email address domain is invalid")

    @classmethod
    def from_raw(cls, value: str) -> Self:
        """Normalize user-supplied spelling into one canonical account identity."""
        if type(value) is not str:
            raise TypeError("email address must be a string")
        return cls(value.strip().casefold())

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class UserAccount:
    """A persisted account without sessions, tokens, or wellness data."""

    user_id: UserId
    email: EmailAddress
    password_hash: str = field(repr=False)
    is_active: bool

    def __post_init__(self) -> None:
        if type(self.user_id) is not UserId:
            raise TypeError("user_id must be a UserId")
        if type(self.email) is not EmailAddress:
            raise TypeError("email must be an EmailAddress")
        if type(self.password_hash) is not str or not self.password_hash.strip():
            raise ValueError("password_hash must be a nonblank string")
        if type(self.is_active) is not bool:
            raise TypeError("is_active must be a boolean")
