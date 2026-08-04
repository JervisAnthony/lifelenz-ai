"""Behavior tests for process-local in-memory repository implementations."""

import inspect
from datetime import UTC, date, datetime, timedelta
from typing import get_args, get_type_hints

import pytest

import lifelenz.domain
import lifelenz.repositories
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
    DuplicateEntityError,
    EntityNotFoundError,
    GoalRepository,
    InMemoryGoalRepository,
    InMemoryProfileRepository,
    InMemoryWellnessRecordRepository,
    ProfileRepository,
    WellnessRecord,
    WellnessRecordRepository,
    WellnessRecordType,
)

PROFILE_1 = ProfileId("10000000-0000-4000-8000-000000000001")
PROFILE_2 = ProfileId("10000000-0000-4000-8000-000000000002")
PROFILE_3 = ProfileId("10000000-0000-4000-8000-000000000003")
GOAL_1 = GoalId("20000000-0000-4000-8000-000000000001")
GOAL_2 = GoalId("20000000-0000-4000-8000-000000000002")
GOAL_3 = GoalId("20000000-0000-4000-8000-000000000003")
AT_NOON = datetime(2026, 8, 10, 12, tzinfo=UTC)
SUPPORTED_RECORD_TYPES = get_args(WellnessRecord.__value__)


def _profile(profile_id: ProfileId, *, name: str | None = None) -> WellnessProfile:
    return WellnessProfile(profile_id, "UTC", display_name=name)


def _goal(
    goal_id: GoalId,
    profile_id: ProfileId,
    *,
    title: str | None = None,
) -> WellnessGoal:
    return WellnessGoal(
        goal_id=goal_id,
        profile_id=profile_id,
        target=GoalTarget(MetricIdentifier.STEPS, 5_000, MeasurementUnit.COUNT),
        direction=GoalDirection.AT_LEAST,
        status=GoalStatus.ACTIVE,
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
        period = TimeRange(recorded_at - timedelta(hours=8), recorded_at)
        return SleepRecord(metadata, period, sleep_minutes=420, awake_minutes=60)
    if record_type is DailyActivityRecord:
        return DailyActivityRecord(metadata, reporting_date, steps=1_000)
    if record_type is WorkoutRecord:
        period = TimeRange(recorded_at - timedelta(hours=1), recorded_at)
        return WorkoutRecord(metadata, period, WorkoutType.WALKING)
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


def _assert_same_signature(implementation: type[object], protocol: type[object]) -> None:
    for name in protocol.__dict__:
        if name.startswith("_") or not callable(getattr(protocol, name)):
            continue
        implementation_method = getattr(implementation, name)
        protocol_method = getattr(protocol, name)
        assert (
            inspect.signature(implementation_method).parameters.keys()
            == inspect.signature(protocol_method).parameters.keys()
        )
        assert get_type_hints(implementation_method) == get_type_hints(protocol_method)


@pytest.mark.parametrize(
    ("implementation", "protocol"),
    [
        (InMemoryProfileRepository, ProfileRepository),
        (InMemoryGoalRepository, GoalRepository),
        (InMemoryWellnessRecordRepository, WellnessRecordRepository),
    ],
)
def test_implementation_signatures_conform_to_protocol(
    implementation: type[object],
    protocol: type[object],
) -> None:
    _assert_same_signature(implementation, protocol)


@pytest.mark.parametrize(
    ("repository", "listing_method"),
    [
        (InMemoryProfileRepository(), "list_all"),
        (InMemoryGoalRepository(), "list_all"),
        (InMemoryWellnessRecordRepository(), "list_for_profile"),
    ],
)
def test_repository_starts_empty(repository: object, listing_method: str) -> None:
    method = getattr(repository, listing_method)
    result = method(PROFILE_1) if listing_method == "list_for_profile" else method()

    assert result == ()
    assert isinstance(result, tuple)


@pytest.mark.parametrize(
    "repository",
    [InMemoryProfileRepository(), InMemoryGoalRepository(), InMemoryWellnessRecordRepository()],
)
def test_internal_state_is_private(repository: object) -> None:
    assert vars(repository)
    assert all(name.startswith("_") for name in vars(repository))
    assert not hasattr(repository, "storage")
    assert not hasattr(repository, "items")


def test_profile_repository_instances_have_independent_state() -> None:
    first = InMemoryProfileRepository()
    second = InMemoryProfileRepository()
    first.save(_profile(PROFILE_1))

    assert first.exists(PROFILE_1)
    assert not second.exists(PROFILE_1)


def test_profile_save_get_and_upsert_preserve_exact_objects() -> None:
    repository = InMemoryProfileRepository()
    original = _profile(PROFILE_1, name="Original")
    replacement = _profile(PROFILE_1, name="Replacement")

    assert repository.save(original) is None
    assert repository.get(PROFILE_1) is original
    assert repository.save(replacement) is None
    assert repository.get(PROFILE_1) is replacement
    assert repository.get(PROFILE_1) is not original


@pytest.mark.parametrize("invalid", [None, "profile", {}, (), object(), PROFILE_1])
def test_profile_save_rejects_invalid_types(invalid: object) -> None:
    with pytest.raises(TypeError, match="profile must be a WellnessProfile"):
        InMemoryProfileRepository().save(invalid)  # type: ignore[arg-type]


@pytest.mark.parametrize("method_name", ["get", "exists", "remove"])
@pytest.mark.parametrize(
    "invalid",
    [None, PROFILE_1.value, RecordId(PROFILE_1.value), GOAL_1, {}, object()],
)
def test_profile_identifier_methods_reject_wrong_types(
    method_name: str,
    invalid: object,
) -> None:
    with pytest.raises(TypeError, match="profile_id must be a ProfileId"):
        getattr(InMemoryProfileRepository(), method_name)(invalid)


def test_profile_get_and_remove_report_missing_identifier() -> None:
    repository = InMemoryProfileRepository()

    with pytest.raises(EntityNotFoundError, match=rf"wellness profile.*{PROFILE_1.value}"):
        repository.get(PROFILE_1)
    with pytest.raises(EntityNotFoundError, match=rf"wellness profile.*{PROFILE_1.value}"):
        repository.remove(PROFILE_1)


def test_profile_exists_tracks_save_and_remove() -> None:
    repository = InMemoryProfileRepository()

    assert repository.exists(PROFILE_1) is False
    repository.save(_profile(PROFILE_1))
    assert repository.exists(PROFILE_1) is True
    assert repository.remove(PROFILE_1) is None
    assert repository.exists(PROFILE_1) is False


def test_profile_listing_is_sorted_stable_immutable_and_exact() -> None:
    repository = InMemoryProfileRepository()
    profiles = [_profile(PROFILE_3), _profile(PROFILE_1), _profile(PROFILE_2)]
    for profile in profiles:
        repository.save(profile)

    first = repository.list_all()
    second = repository.list_all()
    expected = (profiles[1], profiles[2], profiles[0])

    assert first == expected
    assert all(result is item for result, item in zip(first, expected, strict=True))
    assert first == second
    assert isinstance(first, tuple)


def test_profile_removal_leaves_other_profiles_and_other_repositories_untouched() -> None:
    profiles = InMemoryProfileRepository()
    goals = InMemoryGoalRepository()
    records = InMemoryWellnessRecordRepository()
    profile_1 = _profile(PROFILE_1)
    profile_2 = _profile(PROFILE_2)
    goal = _goal(GOAL_1, PROFILE_1)
    record = _record(HydrationRecord, "shared-record")
    profiles.save(profile_1)
    profiles.save(profile_2)
    goals.save(goal)
    records.save(PROFILE_1, record)

    profiles.remove(PROFILE_1)

    assert profiles.list_all() == (profile_2,)
    assert goals.get(GOAL_1) is goal
    assert records.get(PROFILE_1, record.metadata.record_id) is record


def test_goal_repository_instances_have_independent_state() -> None:
    first = InMemoryGoalRepository()
    second = InMemoryGoalRepository()
    first.save(_goal(GOAL_1, PROFILE_1))

    assert first.exists(GOAL_1)
    assert not second.exists(GOAL_1)


def test_goal_save_get_and_upsert_preserve_exact_objects_without_duplicate_error() -> None:
    repository = InMemoryGoalRepository()
    original = _goal(GOAL_1, PROFILE_1, title="Original")
    replacement = _goal(GOAL_1, PROFILE_2, title="Replacement")

    assert repository.save(original) is None
    assert repository.get(GOAL_1) is original
    try:
        result = repository.save(replacement)
    except DuplicateEntityError as error:  # pragma: no cover - explicit semantic guard
        pytest.fail(f"upsert unexpectedly raised DuplicateEntityError: {error}")
    assert result is None
    assert repository.get(GOAL_1) is replacement


@pytest.mark.parametrize("invalid", [None, "goal", {}, (), PROFILE_1, object()])
def test_goal_save_rejects_invalid_types(invalid: object) -> None:
    with pytest.raises(TypeError, match="goal must be a WellnessGoal"):
        InMemoryGoalRepository().save(invalid)  # type: ignore[arg-type]


@pytest.mark.parametrize("method_name", ["get", "exists", "remove"])
@pytest.mark.parametrize(
    "invalid",
    [None, GOAL_1.value, PROFILE_1, RecordId(GOAL_1.value), {}, object()],
)
def test_goal_identifier_methods_reject_wrong_types(method_name: str, invalid: object) -> None:
    with pytest.raises(TypeError, match="goal_id must be a GoalId"):
        getattr(InMemoryGoalRepository(), method_name)(invalid)


def test_goal_get_and_remove_report_missing_identifier() -> None:
    repository = InMemoryGoalRepository()

    with pytest.raises(EntityNotFoundError, match=rf"wellness goal.*{GOAL_1.value}"):
        repository.get(GOAL_1)
    with pytest.raises(EntityNotFoundError, match=rf"wellness goal.*{GOAL_1.value}"):
        repository.remove(GOAL_1)


def test_goal_exists_tracks_save_and_remove() -> None:
    repository = InMemoryGoalRepository()

    assert repository.exists(GOAL_1) is False
    repository.save(_goal(GOAL_1, PROFILE_1))
    assert repository.exists(GOAL_1) is True
    repository.remove(GOAL_1)
    assert repository.exists(GOAL_1) is False


def test_goal_listings_filter_sort_and_preserve_objects_without_profile_lookup() -> None:
    repository = InMemoryGoalRepository()
    goals = [
        _goal(GOAL_3, PROFILE_1),
        _goal(GOAL_1, PROFILE_1),
        _goal(GOAL_2, PROFILE_2),
    ]
    for goal in goals:
        repository.save(goal)

    assert repository.list_for_profile(PROFILE_3) == ()
    profile_goals = repository.list_for_profile(PROFILE_1)
    all_goals = repository.list_all()

    assert profile_goals == (goals[1], goals[0])
    assert all(
        actual is expected
        for actual, expected in zip(profile_goals, (goals[1], goals[0]), strict=True)
    )
    assert all_goals == (goals[1], goals[2], goals[0])
    assert isinstance(all_goals, tuple)
    assert all_goals == repository.list_all()


def test_goal_list_for_profile_rejects_invalid_profile_id() -> None:
    with pytest.raises(TypeError, match="profile_id must be a ProfileId"):
        InMemoryGoalRepository().list_for_profile(PROFILE_1.value)  # type: ignore[arg-type]


def test_goal_removal_leaves_other_goals_profile_and_records_untouched() -> None:
    goals = InMemoryGoalRepository()
    profiles = InMemoryProfileRepository()
    records = InMemoryWellnessRecordRepository()
    first = _goal(GOAL_1, PROFILE_1)
    second = _goal(GOAL_2, PROFILE_1)
    profile = _profile(PROFILE_1)
    record = _record(HydrationRecord, "hydration-1")
    goals.save(first)
    goals.save(second)
    profiles.save(profile)
    records.save(PROFILE_1, record)

    goals.remove(GOAL_1)

    assert goals.list_all() == (second,)
    assert profiles.get(PROFILE_1) is profile
    assert records.get(PROFILE_1, record.metadata.record_id) is record


def test_record_repository_instances_have_independent_state() -> None:
    first = InMemoryWellnessRecordRepository()
    second = InMemoryWellnessRecordRepository()
    record = _record(HydrationRecord, "hydration-1")
    first.save(PROFILE_1, record)

    assert first.exists(PROFILE_1, record.metadata.record_id)
    assert not second.exists(PROFILE_1, record.metadata.record_id)


@pytest.mark.parametrize("record_type", SUPPORTED_RECORD_TYPES)
def test_record_repository_saves_and_retrieves_every_supported_type(
    record_type: WellnessRecordType,
) -> None:
    repository = InMemoryWellnessRecordRepository()
    record = _record(record_type, f"record-{record_type.__name__}")

    assert repository.save(PROFILE_1, record) is None
    assert repository.get(PROFILE_1, record.metadata.record_id) is record


def test_record_upsert_can_replace_with_a_different_supported_concrete_type() -> None:
    repository = InMemoryWellnessRecordRepository()
    original = _record(HydrationRecord, "shared-id")
    replacement = _record(MealRecord, "shared-id")
    repository.save(PROFILE_1, original)

    assert repository.save(PROFILE_1, replacement) is None
    assert repository.get(PROFILE_1, RecordId("shared-id")) is replacement
    assert repository.list_for_profile(PROFILE_1) == (replacement,)


def test_same_record_id_is_isolated_between_profiles() -> None:
    repository = InMemoryWellnessRecordRepository()
    first = _record(HydrationRecord, "shared-id")
    second = _record(MealRecord, "shared-id")
    repository.save(PROFILE_1, first)
    repository.save(PROFILE_2, second)

    assert repository.get(PROFILE_1, RecordId("shared-id")) is first
    assert repository.get(PROFILE_2, RecordId("shared-id")) is second


@pytest.mark.parametrize(
    ("method_name", "remaining_arguments"),
    [
        ("save", (_record(HydrationRecord, "record"),)),
        ("get", (RecordId("record"),)),
        ("exists", (RecordId("record"),)),
        ("list_for_profile", ()),
        ("list_in_time_range", (TimeRange(AT_NOON, AT_NOON + timedelta(hours=1)),)),
        ("list_by_type", (HydrationRecord,)),
        (
            "list_by_type_in_time_range",
            (HydrationRecord, TimeRange(AT_NOON, AT_NOON + timedelta(hours=1))),
        ),
        ("remove", (RecordId("record"),)),
    ],
)
@pytest.mark.parametrize("invalid", [None, PROFILE_1.value, GOAL_1, RecordId("profile"), {}])
def test_record_repository_rejects_invalid_profile_ids(
    method_name: str,
    remaining_arguments: tuple[object, ...],
    invalid: object,
) -> None:
    repository = InMemoryWellnessRecordRepository()

    with pytest.raises(TypeError, match="profile_id must be a ProfileId"):
        getattr(repository, method_name)(invalid, *remaining_arguments)


@pytest.mark.parametrize(
    "invalid",
    [None, "record", {}, (), object(), _profile(PROFILE_1), _goal(GOAL_1, PROFILE_1)],
)
def test_record_save_rejects_unsupported_objects(invalid: object) -> None:
    with pytest.raises(TypeError, match="record must be a supported concrete wellness record"):
        InMemoryWellnessRecordRepository().save(PROFILE_1, invalid)  # type: ignore[arg-type]


def test_record_save_rejects_unsupported_subclass() -> None:
    class UnsupportedHydrationRecord(HydrationRecord):
        pass

    record = UnsupportedHydrationRecord(_metadata("subclass", AT_NOON), 250)

    with pytest.raises(TypeError, match="supported concrete wellness record"):
        InMemoryWellnessRecordRepository().save(PROFILE_1, record)


@pytest.mark.parametrize("method_name", ["get", "exists", "remove"])
@pytest.mark.parametrize("invalid", [None, "record-id", PROFILE_1, GOAL_1, {}, object()])
def test_record_identifier_methods_reject_wrong_types(method_name: str, invalid: object) -> None:
    with pytest.raises(TypeError, match="record_id must be a RecordId"):
        getattr(InMemoryWellnessRecordRepository(), method_name)(PROFILE_1, invalid)


def test_record_get_and_remove_report_both_missing_ownership_components() -> None:
    repository = InMemoryWellnessRecordRepository()
    record_id = RecordId("missing-record")
    message = rf"wellness record.*{PROFILE_1.value}.*{record_id.value}"

    with pytest.raises(EntityNotFoundError, match=message):
        repository.get(PROFILE_1, record_id)
    with pytest.raises(EntityNotFoundError, match=message):
        repository.remove(PROFILE_1, record_id)


def test_record_exists_is_scoped_and_tracks_removal() -> None:
    repository = InMemoryWellnessRecordRepository()
    record = _record(HydrationRecord, "hydration-1")
    record_id = record.metadata.record_id

    assert repository.exists(PROFILE_1, record_id) is False
    repository.save(PROFILE_1, record)
    assert repository.exists(PROFILE_1, record_id) is True
    assert repository.exists(PROFILE_2, record_id) is False
    repository.remove(PROFILE_1, record_id)
    assert repository.exists(PROFILE_1, record_id) is False


def test_record_listing_is_profile_scoped_sorted_stable_immutable_and_exact() -> None:
    repository = InMemoryWellnessRecordRepository()
    late = _record(MealRecord, "b-id", AT_NOON + timedelta(hours=1))
    same_time_later_id = _record(HydrationRecord, "z-id", AT_NOON)
    same_time_earlier_id = _record(WorkoutRecord, "a-id", AT_NOON)
    other_profile = _record(SleepRecord, "other", AT_NOON - timedelta(hours=1))
    for record in (late, same_time_later_id, same_time_earlier_id):
        repository.save(PROFILE_1, record)
    repository.save(PROFILE_2, other_profile)

    first = repository.list_for_profile(PROFILE_1)
    second = repository.list_for_profile(PROFILE_1)

    assert first == (same_time_earlier_id, same_time_later_id, late)
    assert all(
        actual is expected
        for actual, expected in zip(
            first, (same_time_earlier_id, same_time_later_id, late), strict=True
        )
    )
    assert first == second
    assert isinstance(first, tuple)
    assert repository.list_for_profile(PROFILE_3) == ()


def test_time_range_filter_uses_start_inclusive_end_exclusive_and_profile_scope() -> None:
    repository = InMemoryWellnessRecordRepository()
    time_range = TimeRange(AT_NOON, AT_NOON + timedelta(hours=2))
    before = _record(HydrationRecord, "before", AT_NOON - timedelta(seconds=1))
    at_start = _record(HydrationRecord, "start", AT_NOON)
    inside = _record(MealRecord, "inside", AT_NOON + timedelta(hours=1))
    at_end = _record(HydrationRecord, "end", AT_NOON + timedelta(hours=2))
    after = _record(MealRecord, "after", AT_NOON + timedelta(hours=3))
    other_profile = _record(HydrationRecord, "other-profile", AT_NOON + timedelta(minutes=30))
    for record in (after, at_end, inside, before, at_start):
        repository.save(PROFILE_1, record)
    repository.save(PROFILE_2, other_profile)

    assert repository.list_in_time_range(PROFILE_1, time_range) == (at_start, inside)
    assert repository.list_in_time_range(PROFILE_3, time_range) == ()


def test_time_filter_uses_metadata_instead_of_domain_specific_dates() -> None:
    repository = InMemoryWellnessRecordRepository()
    time_range = TimeRange(AT_NOON, AT_NOON + timedelta(hours=2))
    cycle_domain_inside_metadata_outside = _record(
        MenstrualCycleRecord,
        "cycle-outside",
        AT_NOON - timedelta(days=1),
        domain_date=AT_NOON.date(),
    )
    nutrition_domain_outside_metadata_inside = _record(
        DailyNutritionRecord,
        "nutrition-inside",
        AT_NOON + timedelta(hours=1),
        domain_date=AT_NOON.date() - timedelta(days=30),
    )
    sleep_period_differs_from_metadata = SleepRecord(
        _metadata("sleep-start", AT_NOON),
        TimeRange(AT_NOON - timedelta(days=2), AT_NOON - timedelta(days=2) + timedelta(hours=8)),
        sleep_minutes=420,
        awake_minutes=60,
    )
    for record in (
        cycle_domain_inside_metadata_outside,
        nutrition_domain_outside_metadata_inside,
        sleep_period_differs_from_metadata,
    ):
        repository.save(PROFILE_1, record)

    assert repository.list_in_time_range(PROFILE_1, time_range) == (
        sleep_period_differs_from_metadata,
        nutrition_domain_outside_metadata_inside,
    )


@pytest.mark.parametrize("invalid", [None, (AT_NOON, AT_NOON), "range", {}, object()])
def test_time_filtering_rejects_invalid_time_ranges(invalid: object) -> None:
    repository = InMemoryWellnessRecordRepository()

    with pytest.raises(TypeError, match="time_range must be a TimeRange"):
        repository.list_in_time_range(PROFILE_1, invalid)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="time_range must be a TimeRange"):
        repository.list_by_type_in_time_range(  # type: ignore[arg-type]
            PROFILE_1,
            HydrationRecord,
            invalid,
        )


@pytest.mark.parametrize("record_type", SUPPORTED_RECORD_TYPES)
def test_type_filter_accepts_every_supported_concrete_type(
    record_type: WellnessRecordType,
) -> None:
    repository = InMemoryWellnessRecordRepository()
    expected = _record(record_type, f"record-{record_type.__name__}")
    other = _record(HydrationRecord, f"other-{record_type.__name__}")
    repository.save(PROFILE_1, expected)
    repository.save(PROFILE_2, other)

    assert repository.list_by_type(PROFILE_1, record_type) == (expected,)


@pytest.mark.parametrize(
    "invalid",
    [
        object,
        ProfileId,
        GoalStatus,
        InMemoryProfileRepository,
        "HydrationRecord",
        HydrationRecord,
        None,
        object(),
    ],
)
def test_type_filter_rejects_non_record_classes_and_instances(invalid: object) -> None:
    repository = InMemoryWellnessRecordRepository()
    if invalid is HydrationRecord:
        invalid = _record(HydrationRecord, "instance")

    with pytest.raises(TypeError, match="record_type must be a supported concrete"):
        repository.list_by_type(PROFILE_1, invalid)  # type: ignore[arg-type]


def test_type_filter_rejects_unsupported_record_subclass() -> None:
    class UnsupportedHydrationRecord(HydrationRecord):
        pass

    with pytest.raises(TypeError, match="record_type must be a supported concrete"):
        InMemoryWellnessRecordRepository().list_by_type(  # type: ignore[arg-type]
            PROFILE_1,
            UnsupportedHydrationRecord,
        )


def test_type_filter_matches_exact_type_with_profile_isolation_and_ordering() -> None:
    repository = InMemoryWellnessRecordRepository()
    later = _record(HydrationRecord, "later", AT_NOON + timedelta(hours=1))
    earlier = _record(HydrationRecord, "earlier", AT_NOON)
    wrong_type = _record(MealRecord, "meal", AT_NOON - timedelta(hours=1))
    other_profile = _record(HydrationRecord, "other", AT_NOON - timedelta(hours=2))
    for record in (later, wrong_type, earlier):
        repository.save(PROFILE_1, record)
    repository.save(PROFILE_2, other_profile)

    assert repository.list_by_type(PROFILE_1, HydrationRecord) == (earlier, later)


def test_combined_filter_applies_profile_exact_type_range_boundaries_and_order() -> None:
    repository = InMemoryWellnessRecordRepository()
    time_range = TimeRange(AT_NOON, AT_NOON + timedelta(hours=2))
    start = _record(HydrationRecord, "z-start", AT_NOON)
    inside = _record(HydrationRecord, "a-inside", AT_NOON + timedelta(hours=1))
    end = _record(HydrationRecord, "end", AT_NOON + timedelta(hours=2))
    wrong_type = _record(MealRecord, "meal", AT_NOON + timedelta(minutes=30))
    wrong_profile = _record(HydrationRecord, "other", AT_NOON + timedelta(minutes=15))
    for record in (end, inside, wrong_type, start):
        repository.save(PROFILE_1, record)
    repository.save(PROFILE_2, wrong_profile)

    result = repository.list_by_type_in_time_range(PROFILE_1, HydrationRecord, time_range)

    assert result == (start, inside)
    assert isinstance(result, tuple)
    assert repository.list_by_type_in_time_range(PROFILE_3, HydrationRecord, time_range) == ()


def test_combined_filter_validates_profile_and_record_type() -> None:
    repository = InMemoryWellnessRecordRepository()
    time_range = TimeRange(AT_NOON, AT_NOON + timedelta(hours=1))

    with pytest.raises(TypeError, match="profile_id must be a ProfileId"):
        repository.list_by_type_in_time_range(  # type: ignore[arg-type]
            PROFILE_1.value,
            HydrationRecord,
            time_range,
        )
    with pytest.raises(TypeError, match="record_type must be a supported concrete"):
        repository.list_by_type_in_time_range(  # type: ignore[arg-type]
            PROFILE_1,
            object,
            time_range,
        )


def test_record_remove_is_exact_and_leaves_other_profile_and_records_untouched() -> None:
    repository = InMemoryWellnessRecordRepository()
    removed = _record(HydrationRecord, "shared-id")
    other_profile = _record(MealRecord, "shared-id")
    other_record = _record(SleepRecord, "other-id")
    repository.save(PROFILE_1, removed)
    repository.save(PROFILE_2, other_profile)
    repository.save(PROFILE_1, other_record)

    assert repository.remove(PROFILE_1, removed.metadata.record_id) is None

    assert not repository.exists(PROFILE_1, removed.metadata.record_id)
    assert repository.get(PROFILE_2, other_profile.metadata.record_id) is other_profile
    assert repository.get(PROFILE_1, other_record.metadata.record_id) is other_record


def test_returned_listing_tuple_cannot_mutate_repository_state() -> None:
    repository = InMemoryWellnessRecordRepository()
    record = _record(HydrationRecord, "hydration-1")
    repository.save(PROFILE_1, record)
    result = repository.list_for_profile(PROFILE_1)

    with pytest.raises(TypeError):
        result[0] = _record(MealRecord, "meal-1")  # type: ignore[index]
    assert repository.get(PROFILE_1, record.metadata.record_id) is record


def test_repository_public_api_contains_only_expected_exports() -> None:
    expected = [
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
    ]

    assert lifelenz.repositories.__all__ == expected
    assert expected == sorted(expected)
    assert len(expected) == len(set(expected))
    assert not set(expected) & set(lifelenz.domain.__all__)
    assert lifelenz.repositories.InMemoryProfileRepository is InMemoryProfileRepository
    assert lifelenz.repositories.InMemoryGoalRepository is InMemoryGoalRepository
    assert (
        lifelenz.repositories.InMemoryWellnessRecordRepository is InMemoryWellnessRecordRepository
    )
