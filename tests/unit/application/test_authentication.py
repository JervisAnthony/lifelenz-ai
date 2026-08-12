from dataclasses import replace

import pytest

from lifelenz.application import (
    AccountAlreadyExistsError,
    AccountNotFoundError,
    ApplicationValidationError,
    AuthenticationService,
    InactiveAccountError,
    InvalidCredentialsError,
)
from lifelenz.identity import EmailAddress, UserAccount, UserId
from lifelenz.repositories import DuplicateEntityError, EntityNotFoundError


class Accounts:
    def __init__(self) -> None:
        self.values: dict[UserId, UserAccount] = {}

    def save(self, account: UserAccount) -> None:
        if any(
            a.email == account.email and a.user_id != account.user_id for a in self.values.values()
        ):
            raise DuplicateEntityError
        self.values[account.user_id] = account

    def get(self, user_id: UserId) -> UserAccount:
        try:
            return self.values[user_id]
        except KeyError as error:
            raise EntityNotFoundError from error

    def get_by_email(self, email: EmailAddress) -> UserAccount:
        for account in self.values.values():
            if account.email == email:
                return account
        raise EntityNotFoundError

    def exists(self, user_id: UserId) -> bool:
        return user_id in self.values

    def exists_by_email(self, email: EmailAddress) -> bool:
        return any(account.email == email for account in self.values.values())


class Hasher:
    def hash_password(self, password: str) -> str:
        return f"hashed:{password}"

    def verify_password(self, password: str, password_hash: str) -> bool:
        return password_hash == f"hashed:{password}"


def test_register_creates_only_active_account_and_duplicate_is_translated() -> None:
    accounts = Accounts()
    service = AuthenticationService(accounts, Hasher())
    account = service.register(EmailAddress.from_raw(" User@Example.com "), "long passphrase")
    assert account.email.value == "user@example.com"
    assert account.is_active is True
    assert accounts.values == {account.user_id: account}
    with pytest.raises(AccountAlreadyExistsError):
        service.register(EmailAddress.from_raw("USER@example.com"), "another passphrase")


def test_unknown_email_and_wrong_password_are_indistinguishable() -> None:
    service = AuthenticationService(Accounts(), Hasher())
    email = EmailAddress.from_raw("user@example.com")
    messages = []
    for candidate in (email, EmailAddress.from_raw("unknown@example.com")):
        if candidate == email:
            service.register(email, "correct passphrase")
        with pytest.raises(InvalidCredentialsError) as caught:
            service.authenticate(candidate, "incorrect passphrase")
        messages.append(str(caught.value))
    assert messages == ["Invalid email or password."] * 2


def test_inactive_account_and_missing_account_have_explicit_failures() -> None:
    accounts = Accounts()
    service = AuthenticationService(accounts, Hasher())
    account = service.register(EmailAddress.from_raw("user@example.com"), "correct passphrase")
    accounts.values[account.user_id] = replace(account, is_active=False)
    with pytest.raises(InactiveAccountError):
        service.authenticate(account.email, "correct passphrase")
    with pytest.raises(AccountNotFoundError):
        service.get_account(UserId.new())


@pytest.mark.parametrize("password", ["short", "x" * 257, None])
def test_registration_policy_is_enforced_below_http(password: object) -> None:
    with pytest.raises(ApplicationValidationError) as caught:
        AuthenticationService(Accounts(), Hasher()).register(
            EmailAddress.from_raw("user@example.com"),
            password,  # type: ignore[arg-type]
        )
    assert "short" not in str(caught.value)
