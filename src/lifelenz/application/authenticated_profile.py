"""Account-scoped primary wellness-profile orchestration."""

from lifelenz.application.exceptions import (
    ApplicationValidationError,
    ProfileAccessDeniedError,
    ProfileAlreadyExistsError,
    ProfileNotConfiguredError,
)
from lifelenz.application.ownership import ProfileOwnershipService
from lifelenz.application.services import ProfileService
from lifelenz.domain import ProfileId, WellnessProfile
from lifelenz.identity import UserId


class AuthenticatedProfileService:
    """Enforce one owned primary profile for first-party authenticated use cases."""

    def __init__(
        self,
        profile_service: ProfileService,
        ownership_service: ProfileOwnershipService,
    ) -> None:
        if not isinstance(profile_service, ProfileService):
            raise ApplicationValidationError("profile_service must be a ProfileService")
        if not isinstance(ownership_service, ProfileOwnershipService):
            raise ApplicationValidationError("ownership_service must be a ProfileOwnershipService")
        self._profile_service = profile_service
        self._ownership_service = ownership_service

    def create_profile(self, user_id: UserId, profile: WellnessProfile) -> WellnessProfile:
        """Create and assign the user's only public primary profile with compensation."""
        validated_user = self._require_user_id(user_id)
        validated_profile = self._require_profile(profile)
        if self._ownership_service.list_profile_ids(validated_user):
            raise ProfileAlreadyExistsError("primary wellness profile is already configured")
        self._profile_service.save_profile(validated_profile)
        try:
            self._ownership_service.assign_profile(
                validated_user,
                validated_profile.profile_id,
            )
        except Exception:
            self._profile_service.remove_profile(validated_profile.profile_id)
            raise
        return validated_profile

    def get_profile(self, user_id: UserId) -> WellnessProfile:
        """Resolve and return the authenticated user's single owned profile."""
        profile_id = self._resolve_primary_profile_id(user_id)
        return self._profile_service.get_profile(profile_id)

    def update_profile(self, user_id: UserId, profile: WellnessProfile) -> WellnessProfile:
        """Replace mutable profile configuration while preserving identity and ownership."""
        validated_profile = self._require_profile(profile)
        profile_id = self._resolve_primary_profile_id(user_id)
        if validated_profile.profile_id != profile_id:
            raise ProfileAccessDeniedError("profile access is denied")
        return self._profile_service.save_profile(validated_profile)

    def _resolve_primary_profile_id(self, user_id: UserId) -> ProfileId:
        validated_user = self._require_user_id(user_id)
        profile_ids = self._ownership_service.list_profile_ids(validated_user)
        if not profile_ids:
            raise ProfileNotConfiguredError("primary wellness profile is not configured")
        if len(profile_ids) != 1:
            raise ProfileAccessDeniedError("primary profile ownership is ambiguous")
        profile_id = profile_ids[0]
        self._ownership_service.require_owner(validated_user, profile_id)
        return profile_id

    @staticmethod
    def _require_user_id(user_id: object) -> UserId:
        if type(user_id) is not UserId:
            raise ApplicationValidationError("user_id must be a UserId")
        return user_id

    @staticmethod
    def _require_profile(profile: object) -> WellnessProfile:
        if type(profile) is not WellnessProfile:
            raise ApplicationValidationError("profile must be a WellnessProfile")
        return profile
