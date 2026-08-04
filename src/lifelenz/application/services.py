"""Synchronous application services coordinating domain objects and repositories."""

import inspect
from typing import get_args

from lifelenz.application.exceptions import (
    ApplicationValidationError,
    GoalNotFoundError,
    ProfileNotFoundError,
    WellnessRecordNotFoundError,
)
from lifelenz.domain import (
    GoalId,
    ProfileId,
    RecordId,
    TimeRange,
    WellnessGoal,
    WellnessProfile,
)
from lifelenz.repositories import (
    EntityNotFoundError,
    GoalRepository,
    ProfileRepository,
    WellnessRecord,
    WellnessRecordRepository,
    WellnessRecordType,
)

type _RepositoryShape = tuple[tuple[str, tuple[str, ...]], ...]

_PROFILE_REPOSITORY_SHAPE: _RepositoryShape = (
    ("save", ("profile",)),
    ("get", ("profile_id",)),
    ("exists", ("profile_id",)),
    ("list_all", ()),
    ("remove", ("profile_id",)),
)
_GOAL_REPOSITORY_SHAPE: _RepositoryShape = (
    ("save", ("goal",)),
    ("get", ("goal_id",)),
    ("exists", ("goal_id",)),
    ("list_for_profile", ("profile_id",)),
    ("list_all", ()),
    ("remove", ("goal_id",)),
)
_RECORD_REPOSITORY_SHAPE: _RepositoryShape = (
    ("save", ("profile_id", "record")),
    ("get", ("profile_id", "record_id")),
    ("exists", ("profile_id", "record_id")),
    ("list_for_profile", ("profile_id",)),
    ("list_in_time_range", ("profile_id", "time_range")),
    ("list_by_type", ("profile_id", "record_type")),
    ("list_by_type_in_time_range", ("profile_id", "record_type", "time_range")),
    ("remove", ("profile_id", "record_id")),
)
_SUPPORTED_WELLNESS_RECORD_TYPES: tuple[type[WellnessRecord], ...] = get_args(
    WellnessRecord.__value__
)


def _require_repository(
    repository: object,
    *,
    argument_name: str,
    contract_name: str,
    shape: _RepositoryShape,
) -> None:
    for method_name, parameter_names in shape:
        method = getattr(repository, method_name, None)
        if not callable(method):
            raise ApplicationValidationError(
                f"{argument_name} must satisfy {contract_name}; "
                f"missing compatible {method_name} method"
            )
        try:
            actual_names = tuple(inspect.signature(method).parameters)
        except (TypeError, ValueError) as error:
            raise ApplicationValidationError(
                f"{argument_name} must satisfy {contract_name}; "
                f"could not inspect {method_name} method"
            ) from error
        if actual_names != parameter_names:
            raise ApplicationValidationError(
                f"{argument_name} must satisfy {contract_name}; "
                f"{method_name} must accept {parameter_names!r}, got {actual_names!r}"
            )


def _require_profile_id(profile_id: object) -> ProfileId:
    if not isinstance(profile_id, ProfileId):
        raise ApplicationValidationError(f"profile_id must be a ProfileId; got {profile_id!r}")
    return profile_id


def _require_goal_id(goal_id: object) -> GoalId:
    if not isinstance(goal_id, GoalId):
        raise ApplicationValidationError(f"goal_id must be a GoalId; got {goal_id!r}")
    return goal_id


def _require_record_id(record_id: object) -> RecordId:
    if not isinstance(record_id, RecordId):
        raise ApplicationValidationError(f"record_id must be a RecordId; got {record_id!r}")
    return record_id


def _require_time_range(time_range: object) -> TimeRange:
    if not isinstance(time_range, TimeRange):
        raise ApplicationValidationError(f"time_range must be a TimeRange; got {time_range!r}")
    return time_range


def _require_record(record: object) -> WellnessRecord:
    if type(record) not in _SUPPORTED_WELLNESS_RECORD_TYPES:
        raise ApplicationValidationError(
            f"record must be a supported concrete WellnessRecord; got {record!r}"
        )
    return record  # type: ignore[return-value]


def _require_record_type(record_type: object) -> WellnessRecordType:
    if all(record_type is not supported for supported in _SUPPORTED_WELLNESS_RECORD_TYPES):
        raise ApplicationValidationError(
            f"record_type must be a supported concrete wellness record class; got {record_type!r}"
        )
    return record_type  # type: ignore[return-value]


def _profile_not_found(profile_id: ProfileId) -> ProfileNotFoundError:
    return ProfileNotFoundError(f"wellness profile not found for profile_id={profile_id.value!r}")


def _goal_not_found(goal_id: GoalId) -> GoalNotFoundError:
    return GoalNotFoundError(f"wellness goal not found for goal_id={goal_id.value!r}")


def _record_not_found(
    profile_id: ProfileId,
    record_id: RecordId,
) -> WellnessRecordNotFoundError:
    return WellnessRecordNotFoundError(
        "wellness record not found for "
        f"profile_id={profile_id.value!r}, record_id={record_id.value!r}"
    )


def _require_profile(repository: ProfileRepository, profile_id: ProfileId) -> None:
    try:
        exists = repository.exists(profile_id)
    except EntityNotFoundError as error:
        raise _profile_not_found(profile_id) from error
    if not exists:
        raise _profile_not_found(profile_id)


class ProfileService:
    """Coordinate profile use cases through a storage-independent repository contract."""

    def __init__(self, repository: ProfileRepository) -> None:
        """Require and retain a structurally compatible ProfileRepository privately."""
        _require_repository(
            repository,
            argument_name="repository",
            contract_name="ProfileRepository",
            shape=_PROFILE_REPOSITORY_SHAPE,
        )
        self._repository = repository

    def save_profile(self, profile: WellnessProfile) -> WellnessProfile:
        """Upsert and return the exact supplied immutable WellnessProfile."""
        if not isinstance(profile, WellnessProfile):
            raise ApplicationValidationError(f"profile must be a WellnessProfile; got {profile!r}")
        try:
            self._repository.save(profile)
        except EntityNotFoundError as error:
            raise _profile_not_found(profile.profile_id) from error
        return profile

    def get_profile(self, profile_id: ProfileId) -> WellnessProfile:
        """Return a profile, translating expected repository absence."""
        validated_id = _require_profile_id(profile_id)
        try:
            return self._repository.get(validated_id)
        except EntityNotFoundError as error:
            raise _profile_not_found(validated_id) from error

    def profile_exists(self, profile_id: ProfileId) -> bool:
        """Return whether a validated ProfileId exists without raising for absence."""
        validated_id = _require_profile_id(profile_id)
        try:
            return self._repository.exists(validated_id)
        except EntityNotFoundError as error:
            raise _profile_not_found(validated_id) from error

    def list_profiles(self) -> tuple[WellnessProfile, ...]:
        """Return the repository's immutable, deterministically ordered tuple unchanged."""
        return self._repository.list_all()

    def remove_profile(self, profile_id: ProfileId) -> None:
        """Remove one profile without cascading, translating expected absence."""
        validated_id = _require_profile_id(profile_id)
        try:
            self._repository.remove(validated_id)
        except EntityNotFoundError as error:
            raise _profile_not_found(validated_id) from error


class GoalService:
    """Coordinate goal use cases while enforcing profile existence."""

    def __init__(
        self,
        profile_repository: ProfileRepository,
        goal_repository: GoalRepository,
    ) -> None:
        """Require compatible profile and goal repository contracts privately."""
        _require_repository(
            profile_repository,
            argument_name="profile_repository",
            contract_name="ProfileRepository",
            shape=_PROFILE_REPOSITORY_SHAPE,
        )
        _require_repository(
            goal_repository,
            argument_name="goal_repository",
            contract_name="GoalRepository",
            shape=_GOAL_REPOSITORY_SHAPE,
        )
        self._profile_repository = profile_repository
        self._goal_repository = goal_repository

    def save_goal(self, goal: WellnessGoal) -> WellnessGoal:
        """Require the owner profile, upsert the goal, and return it unchanged.

        No profile preferences, progress, analytics, or inferred status are evaluated.
        """
        if not isinstance(goal, WellnessGoal):
            raise ApplicationValidationError(f"goal must be a WellnessGoal; got {goal!r}")
        _require_profile(self._profile_repository, goal.profile_id)
        try:
            self._goal_repository.save(goal)
        except EntityNotFoundError as error:
            raise _goal_not_found(goal.goal_id) from error
        return goal

    def get_goal(self, goal_id: GoalId) -> WellnessGoal:
        """Return a goal by ID without a profile lookup, translating absence."""
        validated_id = _require_goal_id(goal_id)
        try:
            return self._goal_repository.get(validated_id)
        except EntityNotFoundError as error:
            raise _goal_not_found(validated_id) from error

    def goal_exists(self, goal_id: GoalId) -> bool:
        """Return whether a validated GoalId exists without a profile lookup."""
        validated_id = _require_goal_id(goal_id)
        try:
            return self._goal_repository.exists(validated_id)
        except EntityNotFoundError as error:
            raise _goal_not_found(validated_id) from error

    def list_goals(self) -> tuple[WellnessGoal, ...]:
        """Return every goal in the repository's immutable deterministic order."""
        return self._goal_repository.list_all()

    def list_goals_for_profile(self, profile_id: ProfileId) -> tuple[WellnessGoal, ...]:
        """Require the profile and return its repository-ordered immutable tuple."""
        validated_id = _require_profile_id(profile_id)
        _require_profile(self._profile_repository, validated_id)
        return self._goal_repository.list_for_profile(validated_id)

    def remove_goal(self, goal_id: GoalId) -> None:
        """Remove one goal without cascading, translating expected absence."""
        validated_id = _require_goal_id(goal_id)
        try:
            self._goal_repository.remove(validated_id)
        except EntityNotFoundError as error:
            raise _goal_not_found(validated_id) from error


class WellnessRecordService:
    """Coordinate profile-owned wellness-record use cases without storage coupling."""

    def __init__(
        self,
        profile_repository: ProfileRepository,
        record_repository: WellnessRecordRepository,
    ) -> None:
        """Require compatible profile and wellness-record repositories privately."""
        _require_repository(
            profile_repository,
            argument_name="profile_repository",
            contract_name="ProfileRepository",
            shape=_PROFILE_REPOSITORY_SHAPE,
        )
        _require_repository(
            record_repository,
            argument_name="record_repository",
            contract_name="WellnessRecordRepository",
            shape=_RECORD_REPOSITORY_SHAPE,
        )
        self._profile_repository = profile_repository
        self._record_repository = record_repository

    def save_record(self, profile_id: ProfileId, record: WellnessRecord) -> WellnessRecord:
        """Require the profile, upsert an exact supported record, and return it unchanged."""
        validated_profile_id = _require_profile_id(profile_id)
        validated_record = _require_record(record)
        _require_profile(self._profile_repository, validated_profile_id)
        try:
            self._record_repository.save(validated_profile_id, validated_record)
        except EntityNotFoundError as error:
            raise _record_not_found(
                validated_profile_id,
                validated_record.metadata.record_id,
            ) from error
        return validated_record

    def get_record(self, profile_id: ProfileId, record_id: RecordId) -> WellnessRecord:
        """Require the profile and return the exact owned record, translating absence."""
        validated_profile_id = _require_profile_id(profile_id)
        validated_record_id = _require_record_id(record_id)
        _require_profile(self._profile_repository, validated_profile_id)
        try:
            return self._record_repository.get(validated_profile_id, validated_record_id)
        except EntityNotFoundError as error:
            raise _record_not_found(validated_profile_id, validated_record_id) from error

    def record_exists(self, profile_id: ProfileId, record_id: RecordId) -> bool:
        """Require the profile and return whether its exact record key exists."""
        validated_profile_id = _require_profile_id(profile_id)
        validated_record_id = _require_record_id(record_id)
        _require_profile(self._profile_repository, validated_profile_id)
        try:
            return self._record_repository.exists(validated_profile_id, validated_record_id)
        except EntityNotFoundError as error:
            raise _record_not_found(validated_profile_id, validated_record_id) from error

    def list_records_for_profile(self, profile_id: ProfileId) -> tuple[WellnessRecord, ...]:
        """Require the profile and preserve the repository's immutable ordering."""
        validated_id = _require_profile_id(profile_id)
        _require_profile(self._profile_repository, validated_id)
        return self._record_repository.list_for_profile(validated_id)

    def list_records_in_time_range(
        self,
        profile_id: ProfileId,
        time_range: TimeRange,
    ) -> tuple[WellnessRecord, ...]:
        """Require the profile and delegate metadata timestamp filtering unchanged."""
        validated_id = _require_profile_id(profile_id)
        validated_range = _require_time_range(time_range)
        _require_profile(self._profile_repository, validated_id)
        return self._record_repository.list_in_time_range(validated_id, validated_range)

    def list_records_by_type(
        self,
        profile_id: ProfileId,
        record_type: WellnessRecordType,
    ) -> tuple[WellnessRecord, ...]:
        """Require the profile and delegate exact concrete record-type filtering."""
        validated_id = _require_profile_id(profile_id)
        validated_type = _require_record_type(record_type)
        _require_profile(self._profile_repository, validated_id)
        return self._record_repository.list_by_type(validated_id, validated_type)

    def list_records_by_type_in_time_range(
        self,
        profile_id: ProfileId,
        record_type: WellnessRecordType,
        time_range: TimeRange,
    ) -> tuple[WellnessRecord, ...]:
        """Require the profile and delegate exact-type metadata-time filtering."""
        validated_id = _require_profile_id(profile_id)
        validated_type = _require_record_type(record_type)
        validated_range = _require_time_range(time_range)
        _require_profile(self._profile_repository, validated_id)
        return self._record_repository.list_by_type_in_time_range(
            validated_id,
            validated_type,
            validated_range,
        )

    def remove_record(self, profile_id: ProfileId, record_id: RecordId) -> None:
        """Require the profile and remove one exact record key without cascading."""
        validated_profile_id = _require_profile_id(profile_id)
        validated_record_id = _require_record_id(record_id)
        _require_profile(self._profile_repository, validated_profile_id)
        try:
            self._record_repository.remove(validated_profile_id, validated_record_id)
        except EntityNotFoundError as error:
            raise _record_not_found(validated_profile_id, validated_record_id) from error
