"""Process-local, non-durable implementations of LifeLenz repository contracts."""

from collections.abc import Iterable
from datetime import datetime
from typing import get_args

from lifelenz.domain import GoalId, ProfileId, RecordId, TimeRange, WellnessGoal, WellnessProfile
from lifelenz.repositories.contracts import WellnessRecord, WellnessRecordType
from lifelenz.repositories.exceptions import EntityNotFoundError

_SUPPORTED_WELLNESS_RECORD_TYPES: tuple[type[WellnessRecord], ...] = get_args(
    WellnessRecord.__value__
)


def _require_profile_id(profile_id: object) -> ProfileId:
    if not isinstance(profile_id, ProfileId):
        raise TypeError(f"profile_id must be a ProfileId; got {profile_id!r}")
    return profile_id


def _require_goal_id(goal_id: object) -> GoalId:
    if not isinstance(goal_id, GoalId):
        raise TypeError(f"goal_id must be a GoalId; got {goal_id!r}")
    return goal_id


def _require_record_id(record_id: object) -> RecordId:
    if not isinstance(record_id, RecordId):
        raise TypeError(f"record_id must be a RecordId; got {record_id!r}")
    return record_id


def _require_time_range(time_range: object) -> TimeRange:
    if not isinstance(time_range, TimeRange):
        raise TypeError(f"time_range must be a TimeRange; got {time_range!r}")
    return time_range


def _require_record(record: object) -> WellnessRecord:
    if type(record) not in _SUPPORTED_WELLNESS_RECORD_TYPES:
        raise TypeError(f"record must be a supported concrete wellness record; got {record!r}")
    return record  # type: ignore[return-value]


def _require_record_type(record_type: object) -> WellnessRecordType:
    if all(
        record_type is not supported_type for supported_type in _SUPPORTED_WELLNESS_RECORD_TYPES
    ):
        raise TypeError(
            f"record_type must be a supported concrete wellness record class; got {record_type!r}"
        )
    return record_type  # type: ignore[return-value]


def _record_sort_key(record: WellnessRecord) -> tuple[datetime, str]:
    return record.metadata.recorded_at, record.metadata.record_id.value


class InMemoryProfileRepository:
    """Store profiles in independent, process-local, non-durable memory.

    Instances are intended for tests and early development. They make no thread-safety
    guarantee and lose all stored values when the process ends.
    """

    def __init__(self) -> None:
        """Create an empty repository with private instance-owned state."""
        self._profiles: dict[ProfileId, WellnessProfile] = {}

    def save(self, profile: WellnessProfile) -> None:
        """Upsert and preserve an exact WellnessProfile object by ProfileId."""
        if not isinstance(profile, WellnessProfile):
            raise TypeError(f"profile must be a WellnessProfile; got {profile!r}")
        self._profiles[profile.profile_id] = profile

    def get(self, profile_id: ProfileId) -> WellnessProfile:
        """Return the exact stored profile or raise EntityNotFoundError."""
        validated_id = _require_profile_id(profile_id)
        try:
            return self._profiles[validated_id]
        except KeyError:
            raise EntityNotFoundError(
                f"wellness profile not found for profile_id={validated_id.value!r}"
            ) from None

    def exists(self, profile_id: ProfileId) -> bool:
        """Return whether a validated ProfileId is present."""
        return _require_profile_id(profile_id) in self._profiles

    def list_all(self) -> tuple[WellnessProfile, ...]:
        """Return an immutable tuple ordered by ProfileId.value ascending."""
        return tuple(sorted(self._profiles.values(), key=lambda profile: profile.profile_id.value))

    def remove(self, profile_id: ProfileId) -> None:
        """Remove one profile or raise EntityNotFoundError without cascading."""
        validated_id = _require_profile_id(profile_id)
        try:
            del self._profiles[validated_id]
        except KeyError:
            raise EntityNotFoundError(
                f"wellness profile not found for profile_id={validated_id.value!r}"
            ) from None


class InMemoryGoalRepository:
    """Store goals in independent, process-local, non-durable memory.

    Instances do not validate profile existence, calculate progress, or guarantee
    thread safety. All values are lost when the process ends.
    """

    def __init__(self) -> None:
        """Create an empty repository with private instance-owned state."""
        self._goals: dict[GoalId, WellnessGoal] = {}

    def save(self, goal: WellnessGoal) -> None:
        """Upsert and preserve an exact WellnessGoal object by GoalId."""
        if not isinstance(goal, WellnessGoal):
            raise TypeError(f"goal must be a WellnessGoal; got {goal!r}")
        self._goals[goal.goal_id] = goal

    def get(self, goal_id: GoalId) -> WellnessGoal:
        """Return the exact stored goal or raise EntityNotFoundError."""
        validated_id = _require_goal_id(goal_id)
        try:
            return self._goals[validated_id]
        except KeyError:
            raise EntityNotFoundError(
                f"wellness goal not found for goal_id={validated_id.value!r}"
            ) from None

    def exists(self, goal_id: GoalId) -> bool:
        """Return whether a validated GoalId is present."""
        return _require_goal_id(goal_id) in self._goals

    def list_for_profile(self, profile_id: ProfileId) -> tuple[WellnessGoal, ...]:
        """Return matching goals as a tuple ordered by GoalId.value ascending."""
        validated_id = _require_profile_id(profile_id)
        matches = (goal for goal in self._goals.values() if goal.profile_id == validated_id)
        return tuple(sorted(matches, key=lambda goal: goal.goal_id.value))

    def list_all(self) -> tuple[WellnessGoal, ...]:
        """Return every goal as an immutable tuple ordered by GoalId.value ascending."""
        return tuple(sorted(self._goals.values(), key=lambda goal: goal.goal_id.value))

    def remove(self, goal_id: GoalId) -> None:
        """Remove one goal or raise EntityNotFoundError without cascading."""
        validated_id = _require_goal_id(goal_id)
        try:
            del self._goals[validated_id]
        except KeyError:
            raise EntityNotFoundError(
                f"wellness goal not found for goal_id={validated_id.value!r}"
            ) from None


class InMemoryWellnessRecordRepository:
    """Store profile-owned records in process-local, non-durable memory.

    Records use composite ``(ProfileId, RecordId)`` ownership. Instances do not check
    profile existence, perform cascading deletion, or guarantee thread safety. All
    values are lost when the process ends.
    """

    def __init__(self) -> None:
        """Create an empty repository with private instance-owned state."""
        self._records: dict[tuple[ProfileId, RecordId], WellnessRecord] = {}

    def save(self, profile_id: ProfileId, record: WellnessRecord) -> None:
        """Upsert an exact supported record under its composite ownership key."""
        validated_profile_id = _require_profile_id(profile_id)
        validated_record = _require_record(record)
        self._records[(validated_profile_id, validated_record.metadata.record_id)] = (
            validated_record
        )

    def get(self, profile_id: ProfileId, record_id: RecordId) -> WellnessRecord:
        """Return the exact owned record or raise EntityNotFoundError."""
        validated_profile_id = _require_profile_id(profile_id)
        validated_record_id = _require_record_id(record_id)
        try:
            return self._records[(validated_profile_id, validated_record_id)]
        except KeyError:
            raise EntityNotFoundError(
                "wellness record not found for "
                f"profile_id={validated_profile_id.value!r}, "
                f"record_id={validated_record_id.value!r}"
            ) from None

    def exists(self, profile_id: ProfileId, record_id: RecordId) -> bool:
        """Return whether the validated composite ownership key is present."""
        key = _require_profile_id(profile_id), _require_record_id(record_id)
        return key in self._records

    def list_for_profile(self, profile_id: ProfileId) -> tuple[WellnessRecord, ...]:
        """Return owned records in deterministic metadata timestamp and ID order."""
        validated_id = _require_profile_id(profile_id)
        return self._ordered(
            record for (owner_id, _), record in self._records.items() if owner_id == validated_id
        )

    def list_in_time_range(
        self,
        profile_id: ProfileId,
        time_range: TimeRange,
    ) -> tuple[WellnessRecord, ...]:
        """Return owned records whose metadata timestamps fall in the TimeRange."""
        validated_id = _require_profile_id(profile_id)
        validated_range = _require_time_range(time_range)
        return self._ordered(
            record
            for (owner_id, _), record in self._records.items()
            if owner_id == validated_id
            and validated_range.start <= record.metadata.recorded_at < validated_range.end
        )

    def list_by_type(
        self,
        profile_id: ProfileId,
        record_type: WellnessRecordType,
    ) -> tuple[WellnessRecord, ...]:
        """Return owned records matching one exact supported concrete class."""
        validated_id = _require_profile_id(profile_id)
        validated_type = _require_record_type(record_type)
        return self._ordered(
            record
            for (owner_id, _), record in self._records.items()
            if owner_id == validated_id and type(record) is validated_type
        )

    def list_by_type_in_time_range(
        self,
        profile_id: ProfileId,
        record_type: WellnessRecordType,
        time_range: TimeRange,
    ) -> tuple[WellnessRecord, ...]:
        """Return exact-type owned records with metadata timestamps in the range."""
        validated_id = _require_profile_id(profile_id)
        validated_type = _require_record_type(record_type)
        validated_range = _require_time_range(time_range)
        return self._ordered(
            record
            for (owner_id, _), record in self._records.items()
            if owner_id == validated_id
            and type(record) is validated_type
            and validated_range.start <= record.metadata.recorded_at < validated_range.end
        )

    def remove(self, profile_id: ProfileId, record_id: RecordId) -> None:
        """Remove one exact ownership key or raise EntityNotFoundError without cascading."""
        validated_profile_id = _require_profile_id(profile_id)
        validated_record_id = _require_record_id(record_id)
        try:
            del self._records[(validated_profile_id, validated_record_id)]
        except KeyError:
            raise EntityNotFoundError(
                "wellness record not found for "
                f"profile_id={validated_profile_id.value!r}, "
                f"record_id={validated_record_id.value!r}"
            ) from None

    @staticmethod
    def _ordered(records: Iterable[WellnessRecord]) -> tuple[WellnessRecord, ...]:
        return tuple(sorted(records, key=_record_sort_key))
