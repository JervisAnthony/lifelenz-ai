"""Behavior tests for framework-independent wellness application services."""

import inspect
from datetime import UTC, date, datetime, timedelta
from typing import get_args

import pytest

import lifelenz.application
import lifelenz.domain
import lifelenz.repositories
from lifelenz.application import (
    ApplicationValidationError,
    GoalNotFoundError,
    GoalService,
    ProfileNotFoundError,
    ProfileService,
    WellnessRecordNotFoundError,
    WellnessRecordService,
)
from lifelenz.domain import (
    BodyMeasurementRecord,
    DailyActivityRecord,
    DailyNutritionRecord,
    DataSource,
    GoalDirection,
    GoalId,
    GoalStatus,
    GoalTarget,
    HydrationRecord,
    MealNutrition,
    MealRecord,
    MealType,
    MeasurementUnit,
    MenstrualBleedingRecord,
    MenstrualCycleRecord,
    MenstrualFlow,
    MetricIdentifier,
    ProfileId,
    RecordId,
    RecordMetadata,
    SleepRecord,
    SubjectiveScore,
    SubjectiveWellnessCheckIn,
    TimeRange,
    WellnessGoal,
    WellnessProfile,
    WorkoutRecord,
    WorkoutType,
)
from lifelenz.repositories import (
    EntityNotFoundError,
    InMemoryGoalRepository,
    InMemoryProfileRepository,
    InMemoryWellnessRecordRepository,
    RepositoryError,
    WellnessRecord,
    WellnessRecordType,
)

PROFILE_1 = ProfileId("10000000-0000-4000-8000-000000000001")
PROFILE_2 = ProfileId("10000000-0000-4000-8000-000000000002")
PROFILE_3 = ProfileId("10000000-0000-4000-8000-000000000003")
GOAL_1 = GoalId("20000000-0000-4000-8000-000000000001")
GOAL_2 = GoalId("20000000-0000-4000-8000-000000000002")
GOAL_3 = GoalId("20000000-0000-4000-8000-000000000003")
AT_NOON = datetime(2026, 8, 11, 12, tzinfo=UTC)
SUPPORTED_RECORD_TYPES = get_args(WellnessRecord.__value__)


def _profile(profile_id: ProfileId, *, name: str | None = None) -> WellnessProfile:
    return WellnessProfile(profile_id, "UTC", display_name=name)


def _goal(
    goal_id: GoalId,
    profile_id: ProfileId,
    *,
    title: str | None = None,
    status: GoalStatus = GoalStatus.ACTIVE,
) -> WellnessGoal:
    return WellnessGoal(
        goal_id=goal_id,
        profile_id=profile_id,
        target=GoalTarget(MetricIdentifier.STEPS, 5_000, MeasurementUnit.COUNT),
        direction=GoalDirection.AT_LEAST,
        status=status,
        title=title,
    )


def _metadata(record_id: str, recorded_at: datetime) -> RecordMetadata:
    return RecordMetadata(RecordId(record_id), recorded_at, DataSource.MANUAL)


def _record(
    record_type: WellnessRecordType,
    record_id: str,
    recorded_at: datetime = AT_NOON,
    *,
    domain_date: date | None = None,
) -> WellnessRecord:
    metadata = _metadata(record_id, recorded_at)
    reporting_date = domain_date or recorded_at.date()
    if record_type is SleepRecord:
        return SleepRecord(
            metadata,
            TimeRange(recorded_at - timedelta(hours=8), recorded_at),
            sleep_minutes=420,
            awake_minutes=60,
        )
    if record_type is DailyActivityRecord:
        return DailyActivityRecord(metadata, reporting_date, steps=1_000)
    if record_type is WorkoutRecord:
        return WorkoutRecord(
            metadata,
            TimeRange(recorded_at - timedelta(hours=1), recorded_at),
            WorkoutType.WALKING,
        )
    if record_type is HydrationRecord:
        return HydrationRecord(metadata, 250)
    if record_type is MealRecord:
        return MealRecord(metadata, MealType.LUNCH, MealNutrition(calories_kcal=400))
    if record_type is DailyNutritionRecord:
        return DailyNutritionRecord(
            metadata,
            reporting_date,
            MealNutrition(calories_kcal=1_800),
            meal_count=3,
        )
    if record_type is BodyMeasurementRecord:
        return BodyMeasurementRecord(metadata, weight_kilograms=70)
    if record_type is SubjectiveWellnessCheckIn:
        return SubjectiveWellnessCheckIn(
            metadata,
            SubjectiveScore(6),
            SubjectiveScore(7),
            SubjectiveScore(4),
        )
    if record_type is MenstrualBleedingRecord:
        return MenstrualBleedingRecord(metadata, MenstrualFlow.MODERATE)
    if record_type is MenstrualCycleRecord:
        return MenstrualCycleRecord(metadata, reporting_date)
    raise AssertionError(f"unsupported test record type: {record_type!r}")


class ConfigurableProfileRepository:
    def __init__(
        self,
        *,
        exists: bool = True,
        failure_method: str | None = None,
        failure: Exception | None = None,
        profiles: tuple[WellnessProfile, ...] = (),
    ) -> None:
        self.present = exists
        self.failure_method = failure_method
        self.failure = failure
        self.profiles = profiles
        self.calls: list[tuple[str, object]] = []

    def _fail(self, method: str) -> None:
        if self.failure_method == method and self.failure is not None:
            raise self.failure

    def save(self, profile: WellnessProfile) -> None:
        self.calls.append(("save", profile))
        self._fail("save")

    def get(self, profile_id: ProfileId) -> WellnessProfile:
        self.calls.append(("get", profile_id))
        self._fail("get")
        return self.profiles[0]

    def exists(self, profile_id: ProfileId) -> bool:
        self.calls.append(("exists", profile_id))
        self._fail("exists")
        return self.present

    def list_all(self) -> tuple[WellnessProfile, ...]:
        self.calls.append(("list_all", ()))
        self._fail("list_all")
        return self.profiles

    def remove(self, profile_id: ProfileId) -> None:
        self.calls.append(("remove", profile_id))
        self._fail("remove")


class ConfigurableGoalRepository:
    def __init__(
        self,
        *,
        exists: bool = True,
        failure_method: str | None = None,
        failure: Exception | None = None,
        goals: tuple[WellnessGoal, ...] = (),
    ) -> None:
        self.present = exists
        self.failure_method = failure_method
        self.failure = failure
        self.goals = goals
        self.calls: list[tuple[str, object]] = []

    def _fail(self, method: str) -> None:
        if self.failure_method == method and self.failure is not None:
            raise self.failure

    def save(self, goal: WellnessGoal) -> None:
        self.calls.append(("save", goal))
        self._fail("save")

    def get(self, goal_id: GoalId) -> WellnessGoal:
        self.calls.append(("get", goal_id))
        self._fail("get")
        return self.goals[0]

    def exists(self, goal_id: GoalId) -> bool:
        self.calls.append(("exists", goal_id))
        self._fail("exists")
        return self.present

    def list_for_profile(self, profile_id: ProfileId) -> tuple[WellnessGoal, ...]:
        self.calls.append(("list_for_profile", profile_id))
        self._fail("list_for_profile")
        return self.goals

    def list_all(self) -> tuple[WellnessGoal, ...]:
        self.calls.append(("list_all", ()))
        self._fail("list_all")
        return self.goals

    def remove(self, goal_id: GoalId) -> None:
        self.calls.append(("remove", goal_id))
        self._fail("remove")


class ConfigurableRecordRepository:
    def __init__(
        self,
        *,
        exists: bool = True,
        failure_method: str | None = None,
        failure: Exception | None = None,
        records: tuple[WellnessRecord, ...] = (),
    ) -> None:
        self.present = exists
        self.failure_method = failure_method
        self.failure = failure
        self.records = records
        self.calls: list[tuple[str, object]] = []

    def _fail(self, method: str) -> None:
        if self.failure_method == method and self.failure is not None:
            raise self.failure

    def save(self, profile_id: ProfileId, record: WellnessRecord) -> None:
        self.calls.append(("save", (profile_id, record)))
        self._fail("save")

    def get(self, profile_id: ProfileId, record_id: RecordId) -> WellnessRecord:
        self.calls.append(("get", (profile_id, record_id)))
        self._fail("get")
        return self.records[0]

    def exists(self, profile_id: ProfileId, record_id: RecordId) -> bool:
        self.calls.append(("exists", (profile_id, record_id)))
        self._fail("exists")
        return self.present

    def list_for_profile(self, profile_id: ProfileId) -> tuple[WellnessRecord, ...]:
        self.calls.append(("list_for_profile", profile_id))
        self._fail("list_for_profile")
        return self.records

    def list_in_time_range(
        self,
        profile_id: ProfileId,
        time_range: TimeRange,
    ) -> tuple[WellnessRecord, ...]:
        self.calls.append(("list_in_time_range", (profile_id, time_range)))
        self._fail("list_in_time_range")
        return self.records

    def list_by_type(
        self,
        profile_id: ProfileId,
        record_type: WellnessRecordType,
    ) -> tuple[WellnessRecord, ...]:
        self.calls.append(("list_by_type", (profile_id, record_type)))
        self._fail("list_by_type")
        return self.records

    def list_by_type_in_time_range(
        self,
        profile_id: ProfileId,
        record_type: WellnessRecordType,
        time_range: TimeRange,
    ) -> tuple[WellnessRecord, ...]:
        self.calls.append(("list_by_type_in_time_range", (profile_id, record_type, time_range)))
        self._fail("list_by_type_in_time_range")
        return self.records

    def remove(self, profile_id: ProfileId, record_id: RecordId) -> None:
        self.calls.append(("remove", (profile_id, record_id)))
        self._fail("remove")


@pytest.mark.parametrize(
    ("service_type", "arguments"),
    [
        (ProfileService, (InMemoryProfileRepository(),)),
        (GoalService, (InMemoryProfileRepository(), InMemoryGoalRepository())),
        (
            WellnessRecordService,
            (InMemoryProfileRepository(), InMemoryWellnessRecordRepository()),
        ),
        (ProfileService, (ConfigurableProfileRepository(),)),
        (GoalService, (ConfigurableProfileRepository(), ConfigurableGoalRepository())),
        (
            WellnessRecordService,
            (ConfigurableProfileRepository(), ConfigurableRecordRepository()),
        ),
    ],
)
def test_service_constructors_accept_structural_repository_contracts(
    service_type: type[object],
    arguments: tuple[object, ...],
) -> None:
    service = service_type(*arguments)

    assert service is not None
    assert all(name.startswith("_") for name in vars(service))


@pytest.mark.parametrize(
    ("factory", "match"),
    [
        (lambda: ProfileService(None), "repository must satisfy ProfileRepository"),
        (
            lambda: ProfileService(InMemoryGoalRepository()),
            "repository must satisfy ProfileRepository",
        ),
        (
            lambda: GoalService(None, InMemoryGoalRepository()),
            "profile_repository must satisfy ProfileRepository",
        ),
        (
            lambda: GoalService(InMemoryProfileRepository(), None),
            "goal_repository must satisfy GoalRepository",
        ),
        (
            lambda: GoalService(InMemoryProfileRepository(), InMemoryProfileRepository()),
            "goal_repository must satisfy GoalRepository",
        ),
        (
            lambda: WellnessRecordService(None, InMemoryWellnessRecordRepository()),
            "profile_repository must satisfy ProfileRepository",
        ),
        (
            lambda: WellnessRecordService(InMemoryProfileRepository(), None),
            "record_repository must satisfy WellnessRecordRepository",
        ),
        (
            lambda: WellnessRecordService(
                InMemoryProfileRepository(),
                InMemoryGoalRepository(),
            ),
            "record_repository must satisfy WellnessRecordRepository",
        ),
        (lambda: ProfileService(object()), "repository must satisfy ProfileRepository"),
    ],
)
def test_service_constructors_reject_invalid_or_wrong_repository_contracts(
    factory: object,
    match: str,
) -> None:
    with pytest.raises(ApplicationValidationError, match=match):
        factory()  # type: ignore[operator]


def test_constructor_translates_uninspectable_dependency_method(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_signature(_: object) -> inspect.Signature:
        raise ValueError("uninspectable")

    monkeypatch.setattr("lifelenz.application.services.inspect.signature", fail_signature)

    with pytest.raises(ApplicationValidationError, match="could not inspect save") as caught:
        ProfileService(InMemoryProfileRepository())
    assert isinstance(caught.value.__cause__, ValueError)


def test_profile_service_save_returns_exact_object_and_upserts() -> None:
    repository = InMemoryProfileRepository()
    service = ProfileService(repository)
    original = _profile(PROFILE_1, name="Original")
    replacement = _profile(PROFILE_1, name="Replacement")

    assert service.save_profile(original) is original
    assert service.save_profile(replacement) is replacement
    assert service.get_profile(PROFILE_1) is replacement


@pytest.mark.parametrize("invalid", [None, "profile", {}, (), PROFILE_1, object()])
def test_profile_service_save_rejects_invalid_profile_before_repository_call(
    invalid: object,
) -> None:
    repository = ConfigurableProfileRepository()

    with pytest.raises(ApplicationValidationError, match="profile must be a WellnessProfile"):
        ProfileService(repository).save_profile(invalid)  # type: ignore[arg-type]
    assert repository.calls == []


@pytest.mark.parametrize("method_name", ["get_profile", "profile_exists", "remove_profile"])
@pytest.mark.parametrize("invalid", [None, PROFILE_1.value, GOAL_1, RecordId("profile"), {}])
def test_profile_service_identifier_methods_validate_before_delegation(
    method_name: str,
    invalid: object,
) -> None:
    repository = ConfigurableProfileRepository()

    with pytest.raises(ApplicationValidationError, match="profile_id must be a ProfileId"):
        getattr(ProfileService(repository), method_name)(invalid)
    assert repository.calls == []


def test_profile_service_get_exists_list_and_remove_behavior() -> None:
    repository = InMemoryProfileRepository()
    service = ProfileService(repository)
    profiles = [_profile(PROFILE_2), _profile(PROFILE_1)]
    for profile in profiles:
        service.save_profile(profile)

    assert service.get_profile(PROFILE_1) is profiles[1]
    assert service.profile_exists(PROFILE_1) is True
    assert service.profile_exists(PROFILE_3) is False
    assert service.list_profiles() == (profiles[1], profiles[0])
    assert isinstance(service.list_profiles(), tuple)
    assert service.remove_profile(PROFILE_1) is None
    assert service.profile_exists(PROFILE_1) is False


def test_profile_service_returns_repository_listing_tuple_unchanged() -> None:
    expected = (_profile(PROFILE_1),)
    repository = ConfigurableProfileRepository(profiles=expected)

    assert ProfileService(repository).list_profiles() is expected


@pytest.mark.parametrize("method_name", ["save", "get", "exists", "remove"])
def test_profile_service_translates_repository_absence_with_chaining(method_name: str) -> None:
    cause = EntityNotFoundError("missing")
    repository = ConfigurableProfileRepository(
        failure_method=method_name,
        failure=cause,
        profiles=(_profile(PROFILE_1),),
    )
    service = ProfileService(repository)
    action = {
        "save": lambda: service.save_profile(_profile(PROFILE_1)),
        "get": lambda: service.get_profile(PROFILE_1),
        "exists": lambda: service.profile_exists(PROFILE_1),
        "remove": lambda: service.remove_profile(PROFILE_1),
    }[method_name]

    with pytest.raises(ProfileNotFoundError, match=PROFILE_1.value) as caught:
        action()
    assert caught.value.__cause__ is cause


def test_profile_service_missing_get_and_remove_translate_without_cascade() -> None:
    profiles = InMemoryProfileRepository()
    goals = InMemoryGoalRepository()
    records = InMemoryWellnessRecordRepository()
    goal = _goal(GOAL_1, PROFILE_1)
    record = _record(HydrationRecord, "record")
    goals.save(goal)
    records.save(PROFILE_1, record)
    service = ProfileService(profiles)

    with pytest.raises(ProfileNotFoundError, match=PROFILE_1.value):
        service.get_profile(PROFILE_1)
    with pytest.raises(ProfileNotFoundError, match=PROFILE_1.value):
        service.remove_profile(PROFILE_1)
    assert goals.get(GOAL_1) is goal
    assert records.get(PROFILE_1, record.metadata.record_id) is record


def test_goal_service_save_requires_profile_and_preserves_goal_exactly() -> None:
    profiles = InMemoryProfileRepository()
    goals = InMemoryGoalRepository()
    profile = _profile(PROFILE_1)
    original = _goal(GOAL_1, PROFILE_1, title="Original", status=GoalStatus.PAUSED)
    replacement = _goal(GOAL_1, PROFILE_1, title="Replacement", status=GoalStatus.PAUSED)
    profiles.save(profile)
    service = GoalService(profiles, goals)

    assert service.save_goal(original) is original
    assert service.save_goal(replacement) is replacement
    assert service.get_goal(GOAL_1) is replacement
    assert replacement.status is GoalStatus.PAUSED


def test_goal_service_missing_profile_prevents_goal_repository_call() -> None:
    profiles = ConfigurableProfileRepository(exists=False)
    goals = ConfigurableGoalRepository()

    with pytest.raises(ProfileNotFoundError, match=PROFILE_1.value):
        GoalService(profiles, goals).save_goal(_goal(GOAL_1, PROFILE_1))
    assert profiles.calls == [("exists", PROFILE_1)]
    assert goals.calls == []


def test_goal_service_translates_profile_repository_absence_with_chaining() -> None:
    cause = EntityNotFoundError("missing profile")
    profiles = ConfigurableProfileRepository(failure_method="exists", failure=cause)

    with pytest.raises(ProfileNotFoundError, match=PROFILE_1.value) as caught:
        GoalService(profiles, ConfigurableGoalRepository()).save_goal(_goal(GOAL_1, PROFILE_1))
    assert caught.value.__cause__ is cause


@pytest.mark.parametrize("invalid", [None, "goal", {}, (), PROFILE_1, object()])
def test_goal_service_save_validates_goal_before_profile_lookup(invalid: object) -> None:
    profiles = ConfigurableProfileRepository()
    goals = ConfigurableGoalRepository()

    with pytest.raises(ApplicationValidationError, match="goal must be a WellnessGoal"):
        GoalService(profiles, goals).save_goal(invalid)  # type: ignore[arg-type]
    assert profiles.calls == []
    assert goals.calls == []


@pytest.mark.parametrize("method_name", ["get_goal", "goal_exists", "remove_goal"])
@pytest.mark.parametrize("invalid", [None, GOAL_1.value, PROFILE_1, RecordId("goal"), {}])
def test_goal_service_identifier_methods_validate_before_delegation(
    method_name: str,
    invalid: object,
) -> None:
    goals = ConfigurableGoalRepository()

    with pytest.raises(ApplicationValidationError, match="goal_id must be a GoalId"):
        getattr(GoalService(ConfigurableProfileRepository(), goals), method_name)(invalid)
    assert goals.calls == []


def test_goal_service_get_exists_and_remove_do_not_lookup_profile() -> None:
    profiles = ConfigurableProfileRepository(exists=False)
    goals = InMemoryGoalRepository()
    goal = _goal(GOAL_1, PROFILE_1)
    goals.save(goal)
    service = GoalService(profiles, goals)

    assert service.get_goal(GOAL_1) is goal
    assert service.goal_exists(GOAL_1) is True
    assert service.goal_exists(GOAL_2) is False
    assert service.remove_goal(GOAL_1) is None
    assert profiles.calls == []


@pytest.mark.parametrize("method_name", ["save", "get", "exists", "remove"])
def test_goal_service_translates_goal_repository_absence_with_chaining(method_name: str) -> None:
    cause = EntityNotFoundError("missing goal")
    profiles = ConfigurableProfileRepository(exists=True)
    goals = ConfigurableGoalRepository(failure_method=method_name, failure=cause)
    service = GoalService(profiles, goals)
    action = {
        "save": lambda: service.save_goal(_goal(GOAL_1, PROFILE_1)),
        "get": lambda: service.get_goal(GOAL_1),
        "exists": lambda: service.goal_exists(GOAL_1),
        "remove": lambda: service.remove_goal(GOAL_1),
    }[method_name]

    with pytest.raises(GoalNotFoundError, match=GOAL_1.value) as caught:
        action()
    assert caught.value.__cause__ is cause


def test_goal_service_listings_preserve_repository_order_and_tuple_identity() -> None:
    goal_1 = _goal(GOAL_1, PROFILE_1)
    goal_2 = _goal(GOAL_2, PROFILE_1)
    expected = (goal_2, goal_1)
    profiles = ConfigurableProfileRepository(exists=True)
    goals = ConfigurableGoalRepository(goals=expected)
    service = GoalService(profiles, goals)

    assert service.list_goals() is expected
    assert service.list_goals_for_profile(PROFILE_1) is expected
    assert goals.calls == [("list_all", ()), ("list_for_profile", PROFILE_1)]


def test_goal_service_existing_profile_without_goals_returns_empty_tuple() -> None:
    profiles = InMemoryProfileRepository()
    profiles.save(_profile(PROFILE_1))

    assert GoalService(profiles, InMemoryGoalRepository()).list_goals_for_profile(PROFILE_1) == ()


def test_goal_service_profile_listing_validates_and_requires_profile() -> None:
    service = GoalService(InMemoryProfileRepository(), InMemoryGoalRepository())

    with pytest.raises(ApplicationValidationError, match="profile_id must be a ProfileId"):
        service.list_goals_for_profile(PROFILE_1.value)  # type: ignore[arg-type]
    with pytest.raises(ProfileNotFoundError, match=PROFILE_1.value):
        service.list_goals_for_profile(PROFILE_1)


def test_goal_service_removal_does_not_modify_profiles_or_records() -> None:
    profiles = InMemoryProfileRepository()
    goals = InMemoryGoalRepository()
    records = InMemoryWellnessRecordRepository()
    profile = _profile(PROFILE_1)
    goal = _goal(GOAL_1, PROFILE_1)
    record = _record(HydrationRecord, "record")
    profiles.save(profile)
    goals.save(goal)
    records.save(PROFILE_1, record)

    GoalService(profiles, goals).remove_goal(GOAL_1)

    assert profiles.get(PROFILE_1) is profile
    assert records.get(PROFILE_1, record.metadata.record_id) is record


@pytest.mark.parametrize("record_type", SUPPORTED_RECORD_TYPES)
def test_record_service_saves_every_supported_type_without_tracked_domain_enforcement(
    record_type: WellnessRecordType,
) -> None:
    profiles = InMemoryProfileRepository()
    records = InMemoryWellnessRecordRepository()
    profiles.save(_profile(PROFILE_1))
    record = _record(record_type, f"record-{record_type.__name__}")
    service = WellnessRecordService(profiles, records)

    assert service.save_record(PROFILE_1, record) is record
    assert service.get_record(PROFILE_1, record.metadata.record_id) is record


def test_record_service_upsert_preserves_exact_replacement_and_metadata() -> None:
    profiles = InMemoryProfileRepository()
    records = InMemoryWellnessRecordRepository()
    profiles.save(_profile(PROFILE_1))
    original = _record(HydrationRecord, "shared")
    replacement = _record(MealRecord, "shared")
    metadata = replacement.metadata
    service = WellnessRecordService(profiles, records)
    service.save_record(PROFILE_1, original)

    assert service.save_record(PROFILE_1, replacement) is replacement
    assert service.get_record(PROFILE_1, RecordId("shared")) is replacement
    assert replacement.metadata is metadata


def test_record_service_missing_profile_prevents_record_repository_call() -> None:
    profiles = ConfigurableProfileRepository(exists=False)
    records = ConfigurableRecordRepository()

    with pytest.raises(ProfileNotFoundError, match=PROFILE_1.value):
        WellnessRecordService(profiles, records).save_record(
            PROFILE_1,
            _record(HydrationRecord, "record"),
        )
    assert records.calls == []


@pytest.mark.parametrize(
    "invalid",
    [None, "record", {}, (), object(), _profile(PROFILE_1), _goal(GOAL_1, PROFILE_1)],
)
def test_record_service_save_rejects_invalid_record_before_repository_calls(
    invalid: object,
) -> None:
    profiles = ConfigurableProfileRepository()
    records = ConfigurableRecordRepository()

    with pytest.raises(ApplicationValidationError, match="supported concrete WellnessRecord"):
        WellnessRecordService(profiles, records).save_record(  # type: ignore[arg-type]
            PROFILE_1,
            invalid,
        )
    assert profiles.calls == []
    assert records.calls == []


def test_record_service_rejects_unsupported_record_subclass() -> None:
    class UnsupportedHydrationRecord(HydrationRecord):
        pass

    record = UnsupportedHydrationRecord(_metadata("subclass", AT_NOON), 250)

    with pytest.raises(ApplicationValidationError, match="supported concrete WellnessRecord"):
        WellnessRecordService(
            ConfigurableProfileRepository(),
            ConfigurableRecordRepository(),
        ).save_record(PROFILE_1, record)


@pytest.mark.parametrize(
    ("method_name", "remaining_arguments"),
    [
        ("save_record", (_record(HydrationRecord, "record"),)),
        ("get_record", (RecordId("record"),)),
        ("record_exists", (RecordId("record"),)),
        ("list_records_for_profile", ()),
        ("list_records_in_time_range", (TimeRange(AT_NOON, AT_NOON + timedelta(hours=1)),)),
        ("list_records_by_type", (HydrationRecord,)),
        (
            "list_records_by_type_in_time_range",
            (HydrationRecord, TimeRange(AT_NOON, AT_NOON + timedelta(hours=1))),
        ),
        ("remove_record", (RecordId("record"),)),
    ],
)
@pytest.mark.parametrize("invalid", [None, PROFILE_1.value, GOAL_1, RecordId("profile"), {}])
def test_record_service_validates_profile_id_before_repository_calls(
    method_name: str,
    remaining_arguments: tuple[object, ...],
    invalid: object,
) -> None:
    profiles = ConfigurableProfileRepository()
    records = ConfigurableRecordRepository()

    with pytest.raises(ApplicationValidationError, match="profile_id must be a ProfileId"):
        getattr(WellnessRecordService(profiles, records), method_name)(
            invalid,
            *remaining_arguments,
        )
    assert profiles.calls == []
    assert records.calls == []


@pytest.mark.parametrize("method_name", ["get_record", "record_exists", "remove_record"])
@pytest.mark.parametrize("invalid", [None, "record", PROFILE_1, GOAL_1, {}, object()])
def test_record_service_validates_record_id_before_profile_lookup(
    method_name: str,
    invalid: object,
) -> None:
    profiles = ConfigurableProfileRepository()
    records = ConfigurableRecordRepository()

    with pytest.raises(ApplicationValidationError, match="record_id must be a RecordId"):
        getattr(WellnessRecordService(profiles, records), method_name)(PROFILE_1, invalid)
    assert profiles.calls == []
    assert records.calls == []


def test_record_service_get_exists_and_profile_ownership_behavior() -> None:
    profiles = InMemoryProfileRepository()
    records = InMemoryWellnessRecordRepository()
    profiles.save(_profile(PROFILE_1))
    profiles.save(_profile(PROFILE_2))
    first = _record(HydrationRecord, "shared")
    second = _record(MealRecord, "shared")
    records.save(PROFILE_1, first)
    records.save(PROFILE_2, second)
    service = WellnessRecordService(profiles, records)

    assert service.get_record(PROFILE_1, RecordId("shared")) is first
    assert service.get_record(PROFILE_2, RecordId("shared")) is second
    assert service.record_exists(PROFILE_1, RecordId("shared")) is True
    assert service.record_exists(PROFILE_1, RecordId("missing")) is False


@pytest.mark.parametrize("method_name", ["save", "get", "exists", "remove"])
def test_record_service_translates_record_repository_absence_with_chaining(
    method_name: str,
) -> None:
    cause = EntityNotFoundError("missing record")
    profiles = ConfigurableProfileRepository(exists=True)
    records = ConfigurableRecordRepository(failure_method=method_name, failure=cause)
    service = WellnessRecordService(profiles, records)
    record = _record(HydrationRecord, "record")
    action = {
        "save": lambda: service.save_record(PROFILE_1, record),
        "get": lambda: service.get_record(PROFILE_1, record.metadata.record_id),
        "exists": lambda: service.record_exists(PROFILE_1, record.metadata.record_id),
        "remove": lambda: service.remove_record(PROFILE_1, record.metadata.record_id),
    }[method_name]

    with pytest.raises(WellnessRecordNotFoundError, match=rf"{PROFILE_1.value}.*record") as caught:
        action()
    assert caught.value.__cause__ is cause


@pytest.mark.parametrize(
    ("method_name", "arguments"),
    [
        ("get_record", (PROFILE_1, RecordId("record"))),
        ("record_exists", (PROFILE_1, RecordId("record"))),
        ("list_records_for_profile", (PROFILE_1,)),
        (
            "list_records_in_time_range",
            (PROFILE_1, TimeRange(AT_NOON, AT_NOON + timedelta(hours=1))),
        ),
        ("list_records_by_type", (PROFILE_1, HydrationRecord)),
        (
            "list_records_by_type_in_time_range",
            (
                PROFILE_1,
                HydrationRecord,
                TimeRange(AT_NOON, AT_NOON + timedelta(hours=1)),
            ),
        ),
        ("remove_record", (PROFILE_1, RecordId("record"))),
    ],
)
def test_record_service_profile_scoped_operations_require_existing_profile(
    method_name: str,
    arguments: tuple[object, ...],
) -> None:
    records = ConfigurableRecordRepository()
    service = WellnessRecordService(ConfigurableProfileRepository(exists=False), records)

    with pytest.raises(ProfileNotFoundError, match=PROFILE_1.value):
        getattr(service, method_name)(*arguments)
    assert records.calls == []


def test_record_service_listing_preserves_repository_tuple_and_order() -> None:
    first = _record(HydrationRecord, "first", AT_NOON)
    second = _record(MealRecord, "second", AT_NOON + timedelta(hours=1))
    expected = (second, first)
    profiles = ConfigurableProfileRepository(exists=True)
    records = ConfigurableRecordRepository(records=expected)
    service = WellnessRecordService(profiles, records)
    time_range = TimeRange(AT_NOON, AT_NOON + timedelta(hours=2))

    assert service.list_records_for_profile(PROFILE_1) is expected
    assert service.list_records_in_time_range(PROFILE_1, time_range) is expected
    assert service.list_records_by_type(PROFILE_1, HydrationRecord) is expected
    assert (
        service.list_records_by_type_in_time_range(PROFILE_1, HydrationRecord, time_range)
        is expected
    )


def test_record_service_existing_profile_with_no_records_returns_empty_tuples() -> None:
    profiles = InMemoryProfileRepository()
    profiles.save(_profile(PROFILE_1))
    service = WellnessRecordService(profiles, InMemoryWellnessRecordRepository())
    time_range = TimeRange(AT_NOON, AT_NOON + timedelta(hours=1))

    assert service.list_records_for_profile(PROFILE_1) == ()
    assert service.list_records_in_time_range(PROFILE_1, time_range) == ()
    assert service.list_records_by_type(PROFILE_1, HydrationRecord) == ()
    assert service.list_records_by_type_in_time_range(PROFILE_1, HydrationRecord, time_range) == ()


def test_record_service_time_filter_preserves_boundaries_and_metadata_semantics() -> None:
    profiles = InMemoryProfileRepository()
    records = InMemoryWellnessRecordRepository()
    profiles.save(_profile(PROFILE_1))
    service = WellnessRecordService(profiles, records)
    time_range = TimeRange(AT_NOON, AT_NOON + timedelta(hours=2))
    start = _record(HydrationRecord, "start", AT_NOON)
    inside = _record(
        DailyNutritionRecord,
        "inside",
        AT_NOON + timedelta(hours=1),
        domain_date=AT_NOON.date() - timedelta(days=30),
    )
    end = _record(HydrationRecord, "end", AT_NOON + timedelta(hours=2))
    for record in (end, inside, start):
        service.save_record(PROFILE_1, record)

    assert service.list_records_in_time_range(PROFILE_1, time_range) == (start, inside)


@pytest.mark.parametrize("invalid", [None, "range", (AT_NOON, AT_NOON), {}, object()])
def test_record_service_time_filters_validate_before_profile_lookup(invalid: object) -> None:
    profiles = ConfigurableProfileRepository()
    records = ConfigurableRecordRepository()
    service = WellnessRecordService(profiles, records)

    with pytest.raises(ApplicationValidationError, match="time_range must be a TimeRange"):
        service.list_records_in_time_range(PROFILE_1, invalid)  # type: ignore[arg-type]
    with pytest.raises(ApplicationValidationError, match="time_range must be a TimeRange"):
        service.list_records_by_type_in_time_range(  # type: ignore[arg-type]
            PROFILE_1,
            HydrationRecord,
            invalid,
        )
    assert profiles.calls == []
    assert records.calls == []


@pytest.mark.parametrize("record_type", SUPPORTED_RECORD_TYPES)
def test_record_service_type_filter_accepts_every_supported_type(
    record_type: WellnessRecordType,
) -> None:
    profiles = InMemoryProfileRepository()
    records = InMemoryWellnessRecordRepository()
    profiles.save(_profile(PROFILE_1))
    record = _record(record_type, f"record-{record_type.__name__}")
    records.save(PROFILE_1, record)

    assert WellnessRecordService(profiles, records).list_records_by_type(
        PROFILE_1,
        record_type,
    ) == (record,)


@pytest.mark.parametrize(
    "invalid",
    [object, ProfileId, GoalStatus, "HydrationRecord", HydrationRecord, None, object()],
)
def test_record_service_type_filters_reject_invalid_types_before_profile_lookup(
    invalid: object,
) -> None:
    profiles = ConfigurableProfileRepository()
    records = ConfigurableRecordRepository()
    if invalid is HydrationRecord:
        invalid = _record(HydrationRecord, "instance")
    service = WellnessRecordService(profiles, records)

    with pytest.raises(ApplicationValidationError, match="record_type must be a supported"):
        service.list_records_by_type(PROFILE_1, invalid)  # type: ignore[arg-type]
    assert profiles.calls == []
    assert records.calls == []


def test_record_service_type_filter_rejects_unsupported_subclass() -> None:
    class UnsupportedHydrationRecord(HydrationRecord):
        pass

    with pytest.raises(ApplicationValidationError, match="record_type must be a supported"):
        WellnessRecordService(
            ConfigurableProfileRepository(),
            ConfigurableRecordRepository(),
        ).list_records_by_type(  # type: ignore[arg-type]
            PROFILE_1,
            UnsupportedHydrationRecord,
        )


def test_record_service_combined_filter_delegates_profile_type_range_and_order() -> None:
    profiles = InMemoryProfileRepository()
    records = InMemoryWellnessRecordRepository()
    profiles.save(_profile(PROFILE_1))
    profiles.save(_profile(PROFILE_2))
    time_range = TimeRange(AT_NOON, AT_NOON + timedelta(hours=2))
    start = _record(HydrationRecord, "start", AT_NOON)
    inside = _record(HydrationRecord, "inside", AT_NOON + timedelta(hours=1))
    end = _record(HydrationRecord, "end", AT_NOON + timedelta(hours=2))
    wrong_type = _record(MealRecord, "meal", AT_NOON + timedelta(minutes=30))
    wrong_profile = _record(HydrationRecord, "other", AT_NOON + timedelta(minutes=15))
    for record in (end, inside, wrong_type, start):
        records.save(PROFILE_1, record)
    records.save(PROFILE_2, wrong_profile)

    assert WellnessRecordService(profiles, records).list_records_by_type_in_time_range(
        PROFILE_1,
        HydrationRecord,
        time_range,
    ) == (start, inside)


def test_record_service_removal_preserves_other_profile_ownership() -> None:
    profiles = InMemoryProfileRepository()
    records = InMemoryWellnessRecordRepository()
    profiles.save(_profile(PROFILE_1))
    profiles.save(_profile(PROFILE_2))
    first = _record(HydrationRecord, "shared")
    second = _record(MealRecord, "shared")
    records.save(PROFILE_1, first)
    records.save(PROFILE_2, second)
    service = WellnessRecordService(profiles, records)

    assert service.remove_record(PROFILE_1, RecordId("shared")) is None
    assert service.get_record(PROFILE_2, RecordId("shared")) is second
    with pytest.raises(WellnessRecordNotFoundError, match="shared"):
        service.get_record(PROFILE_1, RecordId("shared"))


@pytest.mark.parametrize("error", [RepositoryError("repository failure"), RuntimeError("boom")])
@pytest.mark.parametrize("service_kind", ["profile", "goal", "record"])
def test_services_propagate_generic_and_unexpected_repository_failures(
    service_kind: str,
    error: Exception,
) -> None:
    if service_kind == "profile":
        repository = ConfigurableProfileRepository(failure_method="get", failure=error)

        def action() -> object:
            return ProfileService(repository).get_profile(PROFILE_1)

    elif service_kind == "goal":
        repository = ConfigurableGoalRepository(failure_method="get", failure=error)

        def action() -> object:
            return GoalService(ConfigurableProfileRepository(), repository).get_goal(GOAL_1)

    else:
        repository = ConfigurableRecordRepository(failure_method="get", failure=error)

        def action() -> object:
            return WellnessRecordService(
                ConfigurableProfileRepository(),
                repository,
            ).get_record(PROFILE_1, RecordId("record"))

    with pytest.raises(type(error)) as caught:
        action()
    assert caught.value is error


def test_application_public_api_is_exact_sorted_unique_and_isolated() -> None:
    expected = [
        "ApplicationError",
        "ApplicationValidationError",
        "GoalNotFoundError",
        "GoalService",
        "ProfileNotFoundError",
        "ProfileService",
        "WellnessRecordNotFoundError",
        "WellnessRecordService",
    ]

    assert lifelenz.application.__all__ == expected
    assert expected == sorted(expected)
    assert len(expected) == len(set(expected))
    assert not set(expected) & set(lifelenz.domain.__all__)
    assert not set(expected) & set(lifelenz.repositories.__all__)
    assert len(lifelenz.domain.__all__) == 48
    assert len(lifelenz.repositories.__all__) == 11
