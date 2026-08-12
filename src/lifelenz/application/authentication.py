"""Framework- and token-independent account registration and authentication."""

from typing import Protocol

from lifelenz.application.exceptions import (
    AccountAlreadyExistsError,
    AccountNotFoundError,
    ApplicationValidationError,
    InactiveAccountError,
    InvalidCredentialsError,
)
from lifelenz.identity import EmailAddress, UserAccount, UserId
from lifelenz.repositories import DuplicateEntityError, EntityNotFoundError, UserAccountRepository

_MIN_PASSWORD_LENGTH = 12
_MAX_PASSWORD_LENGTH = 256
_INVALID_CREDENTIALS_MESSAGE = "Invalid email or password."


class PasswordHasher(Protocol):
    """Minimal password adapter needed by authentication orchestration."""

    def hash_password(self, password: str) -> str: ...

    def verify_password(self, password: str, password_hash: str) -> bool: ...


class AuthenticationService:
    """Register and authenticate accounts without issuing or interpreting tokens."""

    def __init__(self, repository: UserAccountRepository, password_hasher: PasswordHasher) -> None:
        if repository is None:
            raise ApplicationValidationError("repository is required")
        if password_hasher is None:
            raise ApplicationValidationError("password_hasher is required")
        self._repository = repository
        self._password_hasher = password_hasher

    def register(self, email: EmailAddress, password: str) -> UserAccount:
        """Create only an active account, with repository uniqueness authoritative."""
        self._require_email(email)
        self._validate_registration_password(password)
        if self._repository.exists_by_email(email):
            raise AccountAlreadyExistsError("an account already uses this email")
        account = UserAccount(
            user_id=UserId.new(),
            email=email,
            password_hash=self._password_hasher.hash_password(password),
            is_active=True,
        )
        try:
            self._repository.save(account)
        except DuplicateEntityError as error:
            raise AccountAlreadyExistsError("an account already uses this email") from error
        return account

    def authenticate(self, email: EmailAddress, password: str) -> UserAccount:
        """Return the active account while keeping credential failures indistinguishable."""
        try:
            self._require_email(email)
            self._validate_login_password(password)
            account = self._repository.get_by_email(email)
        except (ApplicationValidationError, EntityNotFoundError) as error:
            raise InvalidCredentialsError(_INVALID_CREDENTIALS_MESSAGE) from error
        if not self._password_hasher.verify_password(password, account.password_hash):
            raise InvalidCredentialsError(_INVALID_CREDENTIALS_MESSAGE)
        if not account.is_active:
            raise InactiveAccountError("account is inactive")
        return account

    def get_account(self, user_id: UserId) -> UserAccount:
        """Translate expected repository absence into an application lookup failure."""
        if type(user_id) is not UserId:
            raise ApplicationValidationError("user_id must be a UserId")
        try:
            return self._repository.get(user_id)
        except EntityNotFoundError as error:
            raise AccountNotFoundError("account was not found") from error

    @staticmethod
    def _require_email(email: object) -> None:
        if type(email) is not EmailAddress:
            raise ApplicationValidationError("email must be an EmailAddress")

    @staticmethod
    def _validate_registration_password(password: object) -> None:
        if (
            type(password) is not str
            or not _MIN_PASSWORD_LENGTH <= len(password) <= _MAX_PASSWORD_LENGTH
        ):
            raise ApplicationValidationError("password must contain between 12 and 256 characters")

    @staticmethod
    def _validate_login_password(password: object) -> None:
        if (
            type(password) is not str
            or not _MIN_PASSWORD_LENGTH <= len(password) <= _MAX_PASSWORD_LENGTH
        ):
            raise ApplicationValidationError("credential input is invalid")
