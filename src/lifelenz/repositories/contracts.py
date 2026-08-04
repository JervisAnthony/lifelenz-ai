"""Framework-independent contracts for storing LifeLenz domain entities.

``WellnessRecord`` explicitly identifies every supported concrete wellness-record
class. ``WellnessRecordType`` represents one of those concrete classes for exact-type
filters; broad classes, value objects, and enums are not supported record types.
"""

from typing import Protocol

from lifelenz.domain import (
    BodyMeasurementRecord,
    DailyActivityRecord,
    DailyNutritionRecord,
    GoalId,
    HydrationRecord,
    MealRecord,
    MenstrualBleedingRecord,
    MenstrualCycleRecord,
    ProfileId,
    RecordId,
    SleepRecord,
    SubjectiveWellnessCheckIn,
    TimeRange,
    WellnessGoal,
    WellnessProfile,
    WorkoutRecord,
)

type WellnessRecord = (
    SleepRecord
    | DailyActivityRecord
    | WorkoutRecord
    | HydrationRecord
    | MealRecord
    | DailyNutritionRecord
    | BodyMeasurementRecord
    | SubjectiveWellnessCheckIn
    | MenstrualBleedingRecord
    | MenstrualCycleRecord
)
"""A concrete wellness record supported by the repository layer."""

type WellnessRecordType = type[WellnessRecord]
"""The exact concrete class of a supported wellness record."""


class ProfileRepository(Protocol):
    """Contract for storing and retrieving wellness profiles."""

    def save(self, profile: WellnessProfile) -> None:
        """Upsert ``profile`` by its ProfileId, inserting or replacing its value."""
        ...

    def get(self, profile_id: ProfileId) -> WellnessProfile:
        """Return ``profile_id`` or raise EntityNotFoundError when it is absent."""
        ...

    def exists(self, profile_id: ProfileId) -> bool:
        """Return whether ``profile_id`` exists; ordinary absence returns False."""
        ...

    def list_all(self) -> tuple[WellnessProfile, ...]:
        """Return an immutable tuple ordered by ProfileId.value ascending."""
        ...

    def remove(self, profile_id: ProfileId) -> None:
        """Remove ``profile_id`` or raise EntityNotFoundError without cascading."""
        ...


class GoalRepository(Protocol):
    """Contract for storing and retrieving user-defined wellness goals."""

    def save(self, goal: WellnessGoal) -> None:
        """Upsert ``goal`` by GoalId without checking whether its profile exists.

        Implementations do not calculate progress or infer lifecycle status.
        """
        ...

    def get(self, goal_id: GoalId) -> WellnessGoal:
        """Return ``goal_id`` or raise EntityNotFoundError when it is absent."""
        ...

    def exists(self, goal_id: GoalId) -> bool:
        """Return whether ``goal_id`` exists; ordinary absence returns False."""
        ...

    def list_for_profile(self, profile_id: ProfileId) -> tuple[WellnessGoal, ...]:
        """Return that profile's goals as a tuple ordered by GoalId.value ascending."""
        ...

    def list_all(self) -> tuple[WellnessGoal, ...]:
        """Return every goal as an immutable tuple ordered by GoalId.value ascending."""
        ...

    def remove(self, goal_id: GoalId) -> None:
        """Remove ``goal_id`` or raise EntityNotFoundError without cascading."""
        ...


class WellnessRecordRepository(Protocol):
    """Contract for profile-owned storage of all supported wellness records."""

    def save(self, profile_id: ProfileId, record: WellnessRecord) -> None:
        """Upsert ``record`` by ``(profile_id, record.metadata.record_id)``.

        Implementations require a supported concrete record but do not check whether
        ``profile_id`` exists, derive ownership from the record, or generate identifiers.
        """
        ...

    def get(self, profile_id: ProfileId, record_id: RecordId) -> WellnessRecord:
        """Return the exact owned record or raise EntityNotFoundError when absent."""
        ...

    def exists(self, profile_id: ProfileId, record_id: RecordId) -> bool:
        """Return whether the ownership key exists; ordinary absence returns False."""
        ...

    def list_for_profile(self, profile_id: ProfileId) -> tuple[WellnessRecord, ...]:
        """Return owned records in deterministic metadata order.

        The immutable tuple is ordered by ``metadata.recorded_at`` ascending, then
        ``metadata.record_id.value`` ascending.
        """
        ...

    def list_in_time_range(
        self,
        profile_id: ProfileId,
        time_range: TimeRange,
    ) -> tuple[WellnessRecord, ...]:
        """Return owned records whose metadata timestamp is within ``time_range``.

        Membership follows TimeRange's start-inclusive, end-exclusive semantics and
        uses only ``record.metadata.recorded_at``. Results use deterministic metadata
        ordering.
        """
        ...

    def list_by_type(
        self,
        profile_id: ProfileId,
        record_type: WellnessRecordType,
    ) -> tuple[WellnessRecord, ...]:
        """Return owned records whose exact concrete type is ``record_type``.

        Implementations use ``type(record) is record_type`` and return an immutable
        tuple in deterministic metadata order.
        """
        ...

    def list_by_type_in_time_range(
        self,
        profile_id: ProfileId,
        record_type: WellnessRecordType,
        time_range: TimeRange,
    ) -> tuple[WellnessRecord, ...]:
        """Return exact-type owned records with metadata timestamps in the range.

        Implementations use ``type(record) is record_type`` and only
        ``record.metadata.recorded_at``. TimeRange's start-inclusive, end-exclusive
        semantics and deterministic metadata ordering apply.
        """
        ...

    def remove(self, profile_id: ProfileId, record_id: RecordId) -> None:
        """Remove the exact ownership key or raise EntityNotFoundError when absent.

        Records with the same identifier under other profiles remain untouched; no cascading
        deletion is performed.
        """
        ...
