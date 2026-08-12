import pytest

from lifelenz.application import (
    ApplicationValidationError,
    ProfileAccessDeniedError,
    ProfileOwnershipService,
)
from lifelenz.domain import ProfileId
from lifelenz.identity import UserId
from lifelenz.repositories import EntityNotFoundError


class Ownership:
    def __init__(self) -> None:
        self.values: dict[ProfileId, UserId] = {}

    def assign(self, user_id: UserId, profile_id: ProfileId) -> None:
        self.values[profile_id] = user_id

    def get_owner(self, profile_id: ProfileId) -> UserId:
        try:
            return self.values[profile_id]
        except KeyError as error:
            raise EntityNotFoundError from error

    def is_owner(self, user_id: UserId, profile_id: ProfileId) -> bool:
        return self.values.get(profile_id) == user_id

    def list_for_user(self, user_id: UserId) -> tuple[ProfileId, ...]:
        return tuple(
            sorted((p for p, u in self.values.items() if u == user_id), key=lambda p: p.value)
        )

    def remove(self, profile_id: ProfileId) -> None:
        del self.values[profile_id]


def test_ownership_assign_check_require_and_list_are_explicit() -> None:
    service = ProfileOwnershipService(Ownership())
    user = UserId.new()
    first = ProfileId("00000000-0000-4000-8000-000000000002")
    second = ProfileId("00000000-0000-4000-8000-000000000001")
    service.assign_profile(user, first)
    service.assign_profile(user, second)
    assert service.is_owner(user, first) is True
    assert service.require_owner(user, first) is None
    assert service.list_profile_ids(user) == (second, first)


def test_missing_and_other_user_ownership_deny_without_owner_disclosure() -> None:
    service = ProfileOwnershipService(Ownership())
    profile = ProfileId.generate()
    owner = UserId.new()
    service.assign_profile(owner, profile)
    for candidate in (UserId.new(), UserId.new()):
        with pytest.raises(ProfileAccessDeniedError) as caught:
            service.require_owner(candidate, profile)
        assert str(owner.value) not in str(caught.value)


def test_wrong_types_fail_before_repository_access() -> None:
    with pytest.raises(ApplicationValidationError):
        ProfileOwnershipService(Ownership()).is_owner(UserId.new(), UserId.new())  # type: ignore[arg-type]
