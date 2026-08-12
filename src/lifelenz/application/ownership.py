"""Explicit deny-by-default profile ownership orchestration."""

from lifelenz.application.exceptions import ApplicationValidationError, ProfileAccessDeniedError
from lifelenz.domain import ProfileId
from lifelenz.identity import UserId
from lifelenz.repositories import ProfileOwnershipRepository


class ProfileOwnershipService:
    """Manage and require the UserId-to-ProfileId authorization boundary."""

    def __init__(self, repository: ProfileOwnershipRepository) -> None:
        if repository is None:
            raise ApplicationValidationError("repository is required")
        self._repository = repository

    def assign_profile(self, user_id: UserId, profile_id: ProfileId) -> None:
        self._validate(user_id, profile_id)
        self._repository.assign(user_id, profile_id)

    def is_owner(self, user_id: UserId, profile_id: ProfileId) -> bool:
        self._validate(user_id, profile_id)
        return self._repository.is_owner(user_id, profile_id)

    def require_owner(self, user_id: UserId, profile_id: ProfileId) -> None:
        self._validate(user_id, profile_id)
        if not self._repository.is_owner(user_id, profile_id):
            raise ProfileAccessDeniedError("profile access is denied")

    def list_profile_ids(self, user_id: UserId) -> tuple[ProfileId, ...]:
        if type(user_id) is not UserId:
            raise ApplicationValidationError("user_id must be a UserId")
        return self._repository.list_for_user(user_id)

    @staticmethod
    def _validate(user_id: object, profile_id: object) -> None:
        if type(user_id) is not UserId:
            raise ApplicationValidationError("user_id must be a UserId")
        if type(profile_id) is not ProfileId:
            raise ApplicationValidationError("profile_id must be a ProfileId")
