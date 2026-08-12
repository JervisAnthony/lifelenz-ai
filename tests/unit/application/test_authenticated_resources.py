from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from lifelenz.application import (
    ApplicationValidationError,
    AuthenticatedProfileService,
    AuthenticatedWellnessRecordService,
    ProfileAccessDeniedError,
    ProfileAlreadyExistsError,
    ProfileNotConfiguredError,
    ProfileOwnershipService,
    ProfileService,
    WellnessRecordService,
)
from lifelenz.domain import (
    DataSource,
    HydrationRecord,
    ProfileId,
    RecordId,
    RecordMetadata,
    TimeRange,
    WellnessProfile,
)
from lifelenz.identity import UserId


def profile() -> WellnessProfile:
    return WellnessProfile(ProfileId.generate(), "UTC", "Test User")


def record() -> HydrationRecord:
    return HydrationRecord(
        RecordMetadata(RecordId.generate(), datetime(2026, 1, 1, tzinfo=UTC), DataSource.MANUAL),
        250,
    )


def profile_orchestrator() -> tuple[AuthenticatedProfileService, Mock, Mock]:
    profiles = Mock(spec=ProfileService)
    ownership = Mock(spec=ProfileOwnershipService)
    return AuthenticatedProfileService(profiles, ownership), profiles, ownership


def test_profile_create_assigns_ownership_and_compensates_assignment_failure() -> None:
    service, profiles, ownership = profile_orchestrator()
    user = UserId.new()
    value = profile()
    ownership.list_profile_ids.return_value = ()

    assert service.create_profile(user, value) is value
    profiles.save_profile.assert_called_once_with(value)
    ownership.assign_profile.assert_called_once_with(user, value.profile_id)

    ownership.assign_profile.side_effect = RuntimeError("ownership storage unavailable")
    second = profile()
    with pytest.raises(RuntimeError, match="ownership storage unavailable"):
        service.create_profile(user, second)
    profiles.remove_profile.assert_called_once_with(second.profile_id)


def test_profile_cardinality_resolution_update_and_validation_are_deny_by_default() -> None:
    service, profiles, ownership = profile_orchestrator()
    user = UserId.new()
    value = profile()
    ownership.list_profile_ids.return_value = (value.profile_id,)
    profiles.get_profile.return_value = value
    profiles.save_profile.return_value = value

    assert service.get_profile(user) is value
    ownership.require_owner.assert_called_with(user, value.profile_id)
    assert service.update_profile(user, value) is value

    with pytest.raises(ProfileAccessDeniedError):
        service.update_profile(user, profile())
    ownership.list_profile_ids.return_value = ()
    with pytest.raises(ProfileNotConfiguredError):
        service.get_profile(user)
    ownership.list_profile_ids.return_value = (ProfileId.generate(), ProfileId.generate())
    with pytest.raises(ProfileAccessDeniedError):
        service.get_profile(user)
    ownership.list_profile_ids.return_value = (value.profile_id,)
    with pytest.raises(ProfileAlreadyExistsError):
        service.create_profile(user, profile())
    with pytest.raises(ApplicationValidationError):
        service.get_profile(value.profile_id)  # type: ignore[arg-type]
    with pytest.raises(ApplicationValidationError):
        service.update_profile(user, object())  # type: ignore[arg-type]


def test_authenticated_profile_constructor_requires_application_services() -> None:
    profiles = Mock(spec=ProfileService)
    ownership = Mock(spec=ProfileOwnershipService)
    with pytest.raises(ApplicationValidationError):
        AuthenticatedProfileService(object(), ownership)  # type: ignore[arg-type]
    with pytest.raises(ApplicationValidationError):
        AuthenticatedProfileService(profiles, object())  # type: ignore[arg-type]


def test_record_orchestrator_scopes_every_operation_and_selects_exact_filter() -> None:
    profiles = Mock(spec=AuthenticatedProfileService)
    records = Mock(spec=WellnessRecordService)
    service = AuthenticatedWellnessRecordService(profiles, records)
    user = UserId.new()
    owner = profile()
    item = record()
    time_range = TimeRange(
        datetime(2026, 1, 1, tzinfo=UTC),
        datetime(2026, 1, 2, tzinfo=UTC),
    )
    profiles.get_profile.return_value = owner
    records.save_record.return_value = item
    records.get_record.return_value = item
    expected = (item,)
    records.list_records_for_profile.return_value = expected
    records.list_records_by_type.return_value = expected
    records.list_records_in_time_range.return_value = expected
    records.list_records_by_type_in_time_range.return_value = expected

    assert service.create_record(user, item) is item
    assert service.get_record(user, item.metadata.record_id) is item
    assert service.list_records(user) == expected
    assert service.list_records(user, record_type=HydrationRecord) == expected
    assert service.list_records(user, time_range=time_range) == expected
    assert (
        service.list_records(user, record_type=HydrationRecord, time_range=time_range) == expected
    )
    records.save_record.assert_called_once_with(owner.profile_id, item)
    records.get_record.assert_called_once_with(owner.profile_id, item.metadata.record_id)
    records.list_records_by_type_in_time_range.assert_called_once_with(
        owner.profile_id, HydrationRecord, time_range
    )


def test_authenticated_record_constructor_requires_application_services() -> None:
    profiles = Mock(spec=AuthenticatedProfileService)
    records = Mock(spec=WellnessRecordService)
    with pytest.raises(ApplicationValidationError):
        AuthenticatedWellnessRecordService(object(), records)  # type: ignore[arg-type]
    with pytest.raises(ApplicationValidationError):
        AuthenticatedWellnessRecordService(profiles, object())  # type: ignore[arg-type]
