"""Account-scoped wellness-record orchestration through primary profile ownership."""

from lifelenz.application.authenticated_profile import AuthenticatedProfileService
from lifelenz.application.exceptions import ApplicationValidationError
from lifelenz.application.services import WellnessRecordService
from lifelenz.domain import RecordId, TimeRange
from lifelenz.identity import UserId
from lifelenz.repositories import WellnessRecord, WellnessRecordType


class AuthenticatedWellnessRecordService:
    """Scope every record operation to the authenticated user's primary profile."""

    def __init__(
        self,
        profile_service: AuthenticatedProfileService,
        record_service: WellnessRecordService,
    ) -> None:
        if not isinstance(profile_service, AuthenticatedProfileService):
            raise ApplicationValidationError(
                "profile_service must be an AuthenticatedProfileService"
            )
        if not isinstance(record_service, WellnessRecordService):
            raise ApplicationValidationError("record_service must be a WellnessRecordService")
        self._profile_service = profile_service
        self._record_service = record_service

    def create_record(self, user_id: UserId, record: WellnessRecord) -> WellnessRecord:
        profile = self._profile_service.get_profile(user_id)
        return self._record_service.save_record(profile.profile_id, record)

    def get_record(self, user_id: UserId, record_id: RecordId) -> WellnessRecord:
        profile = self._profile_service.get_profile(user_id)
        return self._record_service.get_record(profile.profile_id, record_id)

    def update_record(
        self,
        user_id: UserId,
        record_id: RecordId,
        record: WellnessRecord,
    ) -> WellnessRecord:
        """Replace one owned record while preserving its identity and concrete type."""
        profile = self._profile_service.get_profile(user_id)
        existing = self._record_service.get_record(profile.profile_id, record_id)
        if type(existing) is not type(record):
            raise ApplicationValidationError("record_type cannot be changed during correction")
        if record.metadata.record_id != record_id:
            raise ApplicationValidationError("replacement record_id must match the requested record")
        return self._record_service.save_record(profile.profile_id, record)

    def delete_record(self, user_id: UserId, record_id: RecordId) -> None:
        """Remove one record owned by the authenticated user's primary profile."""
        profile = self._profile_service.get_profile(user_id)
        self._record_service.remove_record(profile.profile_id, record_id)

    def list_records(
        self,
        user_id: UserId,
        *,
        record_type: WellnessRecordType | None = None,
        time_range: TimeRange | None = None,
    ) -> tuple[WellnessRecord, ...]:
        profile = self._profile_service.get_profile(user_id)
        profile_id = profile.profile_id
        if record_type is not None and time_range is not None:
            return self._record_service.list_records_by_type_in_time_range(
                profile_id,
                record_type,
                time_range,
            )
        if record_type is not None:
            return self._record_service.list_records_by_type(profile_id, record_type)
        if time_range is not None:
            return self._record_service.list_records_in_time_range(profile_id, time_range)
        return self._record_service.list_records_for_profile(profile_id)
