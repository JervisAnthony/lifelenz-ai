"""Tests for repository protocol structure and documented semantics."""

import inspect
from collections.abc import Callable
from typing import Protocol, get_args, get_type_hints

import pytest

import lifelenz.domain
import lifelenz.repositories
from lifelenz.domain import (
    BodyMeasurementRecord,
    DailyActivityRecord,
    DailyNutritionRecord,
    GoalId,
    GoalStatus,
    GoalTarget,
    HydrationRecord,
    MealRecord,
    MenstrualBleedingRecord,
    MenstrualCycleRecord,
    ProfileId,
    RecordId,
    RecordMetadata,
    SleepRecord,
    SubjectiveWellnessCheckIn,
    TimeRange,
    WellnessGoal,
    WellnessProfile,
    WorkoutRecord,
)
from lifelenz.repositories import (
    GoalRepository,
    ProfileRepository,
    WellnessRecord,
    WellnessRecordRepository,
    WellnessRecordType,
)

EXPECTED_DOMAIN_EXPORTS = (
    "BeverageType",
    "BodyMeasurementRecord",
    "CheckInTag",
    "ConfidenceLevel",
    "CycleSymptom",
    "CycleSymptomEntry",
    "DailyActivityRecord",
    "DailyNutritionRecord",
    "DataSource",
    "DomainValidationError",
    "GoalDirection",
    "GoalId",
    "GoalStatus",
    "GoalTarget",
    "HydrationRecord",
    "InsightSeverity",
    "InvalidIdentifierError",
    "InvalidNumericValueError",
    "InvalidTimeRangeError",
    "InvalidTimestampError",
    "MealNutrition",
    "MealRecord",
    "MealType",
    "MeasurementSystem",
    "MeasurementUnit",
    "MenstrualBleedingRecord",
    "MenstrualCycleRecord",
    "MenstrualFlow",
    "MetricIdentifier",
    "MoodCategory",
    "PerceivedExertion",
    "ProfileId",
    "RecordId",
    "RecordMetadata",
    "SleepQuality",
    "SleepRecord",
    "SleepStageDurations",
    "SubjectiveScore",
    "SubjectiveWellnessCheckIn",
    "SymptomIntensity",
    "TimeRange",
    "TrackedWellnessDomain",
    "WeekStart",
    "WellnessCategory",
    "WellnessGoal",
    "WellnessProfile",
    "WorkoutRecord",
    "WorkoutType",
)
EXPECTED_REPOSITORY_EXPORTS = (
    "DuplicateEntityError",
    "EntityNotFoundError",
    "GoalRepository",
    "InMemoryGoalRepository",
    "InMemoryProfileRepository",
    "InMemoryWellnessRecordRepository",
    "ProfileRepository",
    "RepositoryError",
    "RepositoryPersistenceError",
    "SQLiteGoalRepository",
    "SQLiteProfileRepository",
    "SQLiteWellnessRecordRepository",
    "WellnessRecord",
    "WellnessRecordRepository",
    "WellnessRecordType",
)
EXPECTED_RECORD_TYPES = (
    SleepRecord,
    DailyActivityRecord,
    WorkoutRecord,
    HydrationRecord,
    MealRecord,
    DailyNutritionRecord,
    BodyMeasurementRecord,
    SubjectiveWellnessCheckIn,
    MenstrualBleedingRecord,
    MenstrualCycleRecord,
)


def _method_hints(protocol: type[Protocol], method_name: str) -> dict[str, object]:
    return get_type_hints(getattr(protocol, method_name))


def _method_doc(protocol: type[Protocol], method_name: str) -> str:
    return inspect.getdoc(getattr(protocol, method_name)) or ""


def test_wellness_record_alias_contains_every_concrete_record_exactly_once() -> None:
    members = get_args(WellnessRecord.__value__)

    assert members == EXPECTED_RECORD_TYPES
    assert len(members) == len(set(members))


@pytest.mark.parametrize(
    "excluded_type",
    [
        WellnessProfile,
        WellnessGoal,
        ProfileId,
        GoalId,
        RecordId,
        RecordMetadata,
        GoalTarget,
        GoalStatus,
    ],
)
def test_wellness_record_alias_excludes_non_record_types(excluded_type: type[object]) -> None:
    assert excluded_type not in get_args(WellnessRecord.__value__)


def test_wellness_record_type_is_the_explicit_record_class_alias() -> None:
    record_type_value = WellnessRecordType.__value__
    origin, *arguments = (record_type_value.__origin__, *get_args(record_type_value))

    assert origin is type
    assert arguments == [WellnessRecord]


@pytest.mark.parametrize(
    ("protocol", "expected_methods"),
    [
        (ProfileRepository, {"save", "get", "exists", "list_all", "remove"}),
        (
            GoalRepository,
            {"save", "get", "exists", "list_for_profile", "list_all", "remove"},
        ),
        (
            WellnessRecordRepository,
            {
                "save",
                "get",
                "exists",
                "list_for_profile",
                "list_in_time_range",
                "list_by_type",
                "list_by_type_in_time_range",
                "remove",
            },
        ),
    ],
)
def test_repository_contract_is_a_protocol_with_exact_public_methods(
    protocol: type[Protocol],
    expected_methods: set[str],
) -> None:
    public_callables = {
        name
        for name, value in protocol.__dict__.items()
        if not name.startswith("_") and isinstance(value, Callable)
    }

    assert protocol._is_protocol is True
    assert public_callables == expected_methods
    with pytest.raises(TypeError, match="Protocols cannot be instantiated"):
        protocol()


@pytest.mark.parametrize(
    ("method_name", "expected_hints"),
    [
        ("save", {"profile": WellnessProfile, "return": type(None)}),
        ("get", {"profile_id": ProfileId, "return": WellnessProfile}),
        ("exists", {"profile_id": ProfileId, "return": bool}),
        ("list_all", {"return": tuple[WellnessProfile, ...]}),
        ("remove", {"profile_id": ProfileId, "return": type(None)}),
    ],
)
def test_profile_repository_signatures(
    method_name: str,
    expected_hints: dict[str, object],
) -> None:
    assert _method_hints(ProfileRepository, method_name) == expected_hints


@pytest.mark.parametrize(
    ("method_name", "expected_hints"),
    [
        ("save", {"goal": WellnessGoal, "return": type(None)}),
        ("get", {"goal_id": GoalId, "return": WellnessGoal}),
        ("exists", {"goal_id": GoalId, "return": bool}),
        (
            "list_for_profile",
            {"profile_id": ProfileId, "return": tuple[WellnessGoal, ...]},
        ),
        ("list_all", {"return": tuple[WellnessGoal, ...]}),
        ("remove", {"goal_id": GoalId, "return": type(None)}),
    ],
)
def test_goal_repository_signatures(
    method_name: str,
    expected_hints: dict[str, object],
) -> None:
    assert _method_hints(GoalRepository, method_name) == expected_hints


@pytest.mark.parametrize(
    ("method_name", "expected_hints"),
    [
        (
            "save",
            {"profile_id": ProfileId, "record": WellnessRecord, "return": type(None)},
        ),
        (
            "get",
            {"profile_id": ProfileId, "record_id": RecordId, "return": WellnessRecord},
        ),
        (
            "exists",
            {"profile_id": ProfileId, "record_id": RecordId, "return": bool},
        ),
        (
            "list_for_profile",
            {"profile_id": ProfileId, "return": tuple[WellnessRecord, ...]},
        ),
        (
            "list_in_time_range",
            {
                "profile_id": ProfileId,
                "time_range": TimeRange,
                "return": tuple[WellnessRecord, ...],
            },
        ),
        (
            "list_by_type",
            {
                "profile_id": ProfileId,
                "record_type": WellnessRecordType,
                "return": tuple[WellnessRecord, ...],
            },
        ),
        (
            "list_by_type_in_time_range",
            {
                "profile_id": ProfileId,
                "record_type": WellnessRecordType,
                "time_range": TimeRange,
                "return": tuple[WellnessRecord, ...],
            },
        ),
        (
            "remove",
            {"profile_id": ProfileId, "record_id": RecordId, "return": type(None)},
        ),
    ],
)
def test_wellness_record_repository_signatures(
    method_name: str,
    expected_hints: dict[str, object],
) -> None:
    assert _method_hints(WellnessRecordRepository, method_name) == expected_hints


@pytest.mark.parametrize(
    ("protocol", "method_name", "parameter_names"),
    [
        (ProfileRepository, "save", ("self", "profile")),
        (ProfileRepository, "get", ("self", "profile_id")),
        (ProfileRepository, "exists", ("self", "profile_id")),
        (ProfileRepository, "list_all", ("self",)),
        (ProfileRepository, "remove", ("self", "profile_id")),
        (GoalRepository, "save", ("self", "goal")),
        (GoalRepository, "get", ("self", "goal_id")),
        (GoalRepository, "exists", ("self", "goal_id")),
        (GoalRepository, "list_for_profile", ("self", "profile_id")),
        (GoalRepository, "list_all", ("self",)),
        (GoalRepository, "remove", ("self", "goal_id")),
        (WellnessRecordRepository, "save", ("self", "profile_id", "record")),
        (WellnessRecordRepository, "get", ("self", "profile_id", "record_id")),
        (WellnessRecordRepository, "exists", ("self", "profile_id", "record_id")),
        (WellnessRecordRepository, "list_for_profile", ("self", "profile_id")),
        (
            WellnessRecordRepository,
            "list_in_time_range",
            ("self", "profile_id", "time_range"),
        ),
        (WellnessRecordRepository, "list_by_type", ("self", "profile_id", "record_type")),
        (
            WellnessRecordRepository,
            "list_by_type_in_time_range",
            ("self", "profile_id", "record_type", "time_range"),
        ),
        (WellnessRecordRepository, "remove", ("self", "profile_id", "record_id")),
    ],
)
def test_repository_method_parameter_order(
    protocol: type[Protocol],
    method_name: str,
    parameter_names: tuple[str, ...],
) -> None:
    assert tuple(inspect.signature(getattr(protocol, method_name)).parameters) == parameter_names


@pytest.mark.parametrize(
    ("protocol", "method_name", "phrases"),
    [
        (ProfileRepository, "save", ("Upsert", "ProfileId")),
        (ProfileRepository, "get", ("EntityNotFoundError",)),
        (ProfileRepository, "list_all", ("tuple", "ProfileId.value ascending")),
        (ProfileRepository, "remove", ("EntityNotFoundError", "without cascading")),
        (GoalRepository, "save", ("Upsert", "without checking", "progress", "status")),
        (GoalRepository, "get", ("EntityNotFoundError",)),
        (GoalRepository, "list_for_profile", ("profile", "GoalId.value ascending")),
        (GoalRepository, "list_all", ("tuple", "GoalId.value ascending")),
        (GoalRepository, "remove", ("EntityNotFoundError", "without cascading")),
        (
            WellnessRecordRepository,
            "save",
            ("Upsert", "profile_id", "metadata.record_id", "do not check"),
        ),
        (WellnessRecordRepository, "get", ("owned record", "EntityNotFoundError")),
        (
            WellnessRecordRepository,
            "list_for_profile",
            ("tuple", "metadata.recorded_at", "metadata.record_id.value"),
        ),
        (
            WellnessRecordRepository,
            "list_in_time_range",
            ("start-inclusive", "end-exclusive", "metadata.recorded_at"),
        ),
        (
            WellnessRecordRepository,
            "list_by_type",
            ("exact concrete type", "type(record) is record_type", "tuple"),
        ),
        (
            WellnessRecordRepository,
            "list_by_type_in_time_range",
            (
                "exact-type",
                "type(record) is record_type",
                "metadata.recorded_at",
                "start-inclusive",
                "end-exclusive",
                "deterministic",
            ),
        ),
        (
            WellnessRecordRepository,
            "remove",
            ("exact ownership key", "EntityNotFoundError", "same identifier", "no cascading"),
        ),
    ],
)
def test_contract_method_documents_required_semantics(
    protocol: type[Protocol],
    method_name: str,
    phrases: tuple[str, ...],
) -> None:
    documentation = _method_doc(protocol, method_name)

    for phrase in phrases:
        assert phrase.casefold() in documentation.casefold()


def test_repository_public_api_is_exact_sorted_and_unique() -> None:
    exports = tuple(lifelenz.repositories.__all__)

    assert exports == EXPECTED_REPOSITORY_EXPORTS
    assert exports == tuple(sorted(exports))
    assert len(exports) == len(set(exports))
    for name in exports:
        assert getattr(lifelenz.repositories, name) is not None


def test_domain_public_api_remains_unchanged() -> None:
    exports = tuple(lifelenz.domain.__all__)

    assert exports == EXPECTED_DOMAIN_EXPORTS
    assert not set(EXPECTED_REPOSITORY_EXPORTS) & set(exports)


def test_repository_package_exports_only_intended_concrete_implementations() -> None:
    assert all(
        name.endswith(("Repository", "Error", "Record", "RecordType"))
        for name in EXPECTED_REPOSITORY_EXPORTS
    )
    assert not hasattr(lifelenz.repositories, "SqlProfileRepository")
    assert not hasattr(lifelenz.repositories, "FilesystemProfileRepository")
    assert not hasattr(lifelenz.repositories, "serialize_wellness_profile")
    assert not hasattr(lifelenz.repositories, "deserialize_wellness_record")
