"""Integration tests for durable SQLite wellness repositories."""

import gc
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from lifelenz.application import (
    GoalService,
    ProfileService,
    WellnessRecordService,
    WellnessSummaryService,
)
from lifelenz.domain import (
    BeverageType,
    BodyMeasurementRecord,
    CheckInTag,
    CycleSymptom,
    CycleSymptomEntry,
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
    MeasurementSystem,
    MeasurementUnit,
    MenstrualBleedingRecord,
    MenstrualCycleRecord,
    MenstrualFlow,
    MetricIdentifier,
    MoodCategory,
    PerceivedExertion,
    ProfileId,
    RecordId,
    RecordMetadata,
    SleepQuality,
    SleepRecord,
    SleepStageDurations,
    SubjectiveScore,
    SubjectiveWellnessCheckIn,
    SymptomIntensity,
    TimeRange,
    TrackedWellnessDomain,
    WeekStart,
    WellnessGoal,
    WellnessProfile,
    WorkoutRecord,
    WorkoutType,
)
from lifelenz.repositories import (
    EntityNotFoundError,
    RepositoryPersistenceError,
    SQLiteGoalRepository,
    SQLiteProfileRepository,
    SQLiteWellnessRecordRepository,
)

PROFILE_1 = ProfileId("50000000-0000-4000-8000-000000000001")
PROFILE_2 = ProfileId("50000000-0000-4000-8000-000000000002")
GOAL_1 = GoalId("51000000-0000-4000-8000-000000000001")
GOAL_2 = GoalId("51000000-0000-4000-8000-000000000002")
BASE_TIME = datetime(2026, 10, 1, 8, tzinfo=UTC)


def profile(profile_id: ProfileId, *, name: str | None = None) -> WellnessProfile:
    return WellnessProfile(
        profile_id,
        "Asia/Kolkata",
        name,
        MeasurementSystem.IMPERIAL,
        WeekStart.SUNDAY,
        (TrackedWellnessDomain.SLEEP, TrackedWellnessDomain.ACTIVITY),
    )


def goal(
    goal_id: GoalId,
    profile_id: ProfileId,
    *,
    status: GoalStatus = GoalStatus.ACTIVE,
    direction: GoalDirection = GoalDirection.AT_LEAST,
    title: str | None = None,
) -> WellnessGoal:
    return WellnessGoal(
        goal_id,
        profile_id,
        GoalTarget(MetricIdentifier.STEPS, 8000, MeasurementUnit.COUNT),
        direction,
        status,
        date(2026, 10, 1),
        date(2026, 12, 31),
        title,
        "  Durable goal description  ",
    )


def metadata(
    record_id: str,
    *,
    observed_at: datetime = BASE_TIME,
    source: DataSource = DataSource.MANUAL,
) -> RecordMetadata:
    return RecordMetadata(RecordId(record_id), observed_at, source, "  persisted note  ")


def hydration(
    record_id: str,
    value: int | float = 250,
    *,
    observed_at: datetime = BASE_TIME,
) -> HydrationRecord:
    return HydrationRecord(metadata(record_id, observed_at=observed_at), value, BeverageType.WATER)


def all_records() -> tuple[object, ...]:
    nutrition = MealNutrition(2000, 90, 240, 65, 28)
    return (
        SleepRecord(
            metadata("sleep"),
            TimeRange(BASE_TIME - timedelta(hours=8), BASE_TIME),
            420,
            60,
            SleepQuality.GOOD,
            SleepStageDurations(30, 220, 100, 100),
            2,
        ),
        DailyActivityRecord(metadata("activity"), date(2026, 10, 1), 9000, 6.5, 50, 350),
        WorkoutRecord(
            metadata("workout"),
            TimeRange(BASE_TIME - timedelta(hours=1), BASE_TIME),
            WorkoutType.RUNNING,
            10,
            700,
            PerceivedExertion(8),
            155,
        ),
        hydration("hydration", 375),
        MealRecord(metadata("meal"), MealType.LUNCH, nutrition, "Café lunch"),
        DailyNutritionRecord(metadata("nutrition"), date(2026, 10, 1), nutrition, 3),
        BodyMeasurementRecord(metadata("body"), 72.5, 1.78, 18, 82),
        SubjectiveWellnessCheckIn(
            metadata("checkin"),
            SubjectiveScore(7),
            SubjectiveScore(6),
            SubjectiveScore(4),
            SubjectiveScore(8),
            MoodCategory.HIGH,
            (CheckInTag.RESTED, CheckInTag.FOCUSED),
        ),
        MenstrualBleedingRecord(
            metadata("bleeding"),
            MenstrualFlow.LIGHT,
            (CycleSymptomEntry(CycleSymptom.CRAMPS, SymptomIntensity.MILD),),
        ),
        MenstrualCycleRecord(metadata("cycle"), date(2026, 9, 28), date(2026, 10, 2)),
    )


@contextmanager
def connect(database_path: Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


@pytest.mark.parametrize(
    "repository_type",
    [SQLiteProfileRepository, SQLiteGoalRepository, SQLiteWellnessRecordRepository],
)
def test_new_database_schema_is_complete_versioned_and_idempotent(
    tmp_path: Path, repository_type: type[object]
) -> None:
    database = tmp_path / "wellness.sqlite3"
    repository_type(database)
    repository_type(str(database))

    with connect(database) as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = ?",
                ("table",),
            )
        }
        indexes = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = ?",
                ("index",),
            )
        }
        version = connection.execute(
            "SELECT value FROM schema_metadata WHERE key = ?", ("schema_version",)
        ).fetchone()["value"]
        foreign_keys = tuple(connection.execute("PRAGMA foreign_key_list(wellness_records)"))

    assert tables >= {"schema_metadata", "wellness_profiles", "wellness_goals", "wellness_records"}
    assert indexes >= {
        "idx_wellness_goals_profile_id",
        "idx_wellness_records_profile_recorded_at",
        "idx_wellness_records_profile_type_time",
    }
    assert version == "2"
    assert foreign_keys == ()
    assert tables >= {"user_accounts", "profile_ownership"}


def test_all_repository_construction_orders_share_one_database(tmp_path: Path) -> None:
    database = tmp_path / "shared.sqlite3"
    SQLiteWellnessRecordRepository(database)
    SQLiteGoalRepository(database)
    SQLiteProfileRepository(database)
    SQLiteProfileRepository(database).save(profile(PROFILE_1))
    SQLiteGoalRepository(database).save(goal(GOAL_1, PROFILE_1))
    SQLiteWellnessRecordRepository(database).save(PROFILE_1, hydration("shared"))

    assert SQLiteProfileRepository(database).exists(PROFILE_1)
    assert SQLiteGoalRepository(database).exists(GOAL_1)
    assert SQLiteWellnessRecordRepository(database).exists(PROFILE_1, RecordId("shared"))


@pytest.mark.parametrize("invalid", [None, True, b"db", {}, object(), "", "   ", ":memory:"])
@pytest.mark.parametrize(
    "repository_type",
    [SQLiteProfileRepository, SQLiteGoalRepository, SQLiteWellnessRecordRepository],
)
def test_repository_constructors_reject_invalid_paths(
    invalid: object, repository_type: type[object]
) -> None:
    expected = (
        TypeError
        if invalid is None
        or invalid is True
        or isinstance(invalid, (bytes, dict))
        or type(invalid) is object
        else RepositoryPersistenceError
    )
    with pytest.raises(expected):
        repository_type(invalid)  # type: ignore[call-arg]


@pytest.mark.parametrize(
    "repository_type",
    [SQLiteProfileRepository, SQLiteGoalRepository, SQLiteWellnessRecordRepository],
)
def test_missing_parent_and_directory_paths_raise_persistence_error_with_cause(
    tmp_path: Path, repository_type: type[object]
) -> None:
    for path in (tmp_path / "missing" / "database.sqlite3", tmp_path):
        with pytest.raises(RepositoryPersistenceError) as caught:
            repository_type(path)
        assert caught.value.__cause__ is not None


def test_invalid_and_unsupported_schema_versions_are_rejected(tmp_path: Path) -> None:
    database = tmp_path / "version.sqlite3"
    SQLiteProfileRepository(database)
    for value in ("0", "3", "invalid"):
        with connect(database) as connection:
            connection.execute(
                "UPDATE schema_metadata SET value = ? WHERE key = ?",
                (value, "schema_version"),
            )
        with pytest.raises(RepositoryPersistenceError, match="schema version") as caught:
            SQLiteGoalRepository(database)
        assert caught.value.__cause__ is not None
        with connect(database) as connection:
            connection.execute(
                "UPDATE schema_metadata SET value = ? WHERE key = ?",
                ("2", "schema_version"),
            )


def test_unopenable_non_database_file_translates_sqlite_failure(tmp_path: Path) -> None:
    database = tmp_path / "not-database.sqlite3"
    database.write_bytes(b"not a sqlite database")
    with pytest.raises(RepositoryPersistenceError, match="schema initialization") as caught:
        SQLiteProfileRepository(database)
    assert isinstance(caught.value.__cause__, sqlite3.Error)
    assert "CREATE TABLE" not in str(caught.value)


def test_profile_repository_empty_upsert_ordering_restart_and_missing_behavior(
    tmp_path: Path,
) -> None:
    database = tmp_path / "profiles.sqlite3"
    repository = SQLiteProfileRepository(database)
    first = profile(PROFILE_1, name="Original")
    second = profile(PROFILE_2, name="Zoë 東京")

    assert repository.list_all() == ()
    assert repository.exists(PROFILE_1) is False
    repository.save(second)
    repository.save(first)
    assert repository.exists(PROFILE_1) is True
    assert repository.get(PROFILE_1) == first
    assert repository.get(PROFILE_1) is not first
    assert repository.list_all() == (first, second)

    replacement = profile(PROFILE_1, name="Replacement")
    repository.save(replacement)
    del repository
    gc.collect()
    reopened = SQLiteProfileRepository(database)
    assert reopened.get(PROFILE_1) == replacement
    reopened.remove(PROFILE_1)
    assert reopened.exists(PROFILE_1) is False
    with pytest.raises(EntityNotFoundError):
        reopened.get(PROFILE_1)
    with pytest.raises(EntityNotFoundError):
        reopened.remove(PROFILE_1)


@pytest.mark.parametrize("method", ["get", "exists", "remove"])
@pytest.mark.parametrize("invalid", [None, PROFILE_1.value, GOAL_1, RecordId("profile"), {}])
def test_profile_repository_rejects_wrong_identifier_types(
    tmp_path: Path, method: str, invalid: object
) -> None:
    repository = SQLiteProfileRepository(tmp_path / "profiles.sqlite3")
    with pytest.raises(TypeError):
        getattr(repository, method)(invalid)


def test_profile_save_rejects_wrong_objects_before_mutation(tmp_path: Path) -> None:
    repository = SQLiteProfileRepository(tmp_path / "profiles.sqlite3")
    for invalid in (None, PROFILE_1, {}, object()):
        with pytest.raises(TypeError):
            repository.save(invalid)  # type: ignore[arg-type]
    assert repository.list_all() == ()


def test_goal_repository_upsert_filter_order_restart_and_profile_independence(
    tmp_path: Path,
) -> None:
    database = tmp_path / "goals.sqlite3"
    repository = SQLiteGoalRepository(database)
    first = goal(GOAL_1, PROFILE_1, title="Primer objetivo")
    second = goal(GOAL_2, PROFILE_2, title="目標")

    assert repository.list_all() == ()
    repository.save(second)
    repository.save(first)
    assert repository.exists(GOAL_1) is True
    assert repository.list_all() == (first, second)
    assert repository.list_for_profile(PROFILE_1) == (first,)
    assert repository.list_for_profile(ProfileId("50000000-0000-4000-8000-000000000099")) == ()

    replacement = goal(GOAL_1, PROFILE_2, status=GoalStatus.PAUSED, title="Changed")
    repository.save(replacement)
    reopened = SQLiteGoalRepository(database)
    assert reopened.get(GOAL_1) == replacement
    assert reopened.list_for_profile(PROFILE_1) == ()
    assert reopened.list_for_profile(PROFILE_2) == (replacement, second)
    reopened.remove(GOAL_1)
    with pytest.raises(EntityNotFoundError):
        reopened.get(GOAL_1)
    with pytest.raises(EntityNotFoundError):
        reopened.remove(GOAL_1)


@pytest.mark.parametrize("direction", tuple(GoalDirection))
@pytest.mark.parametrize("status", tuple(GoalStatus))
def test_goal_repository_round_trips_all_directions_and_statuses(
    tmp_path: Path, direction: GoalDirection, status: GoalStatus
) -> None:
    database = tmp_path / f"{direction.value}-{status.value}.sqlite3"
    repository = SQLiteGoalRepository(database)
    value = goal(GOAL_1, PROFILE_1, direction=direction, status=status)
    repository.save(value)
    assert SQLiteGoalRepository(database).get(GOAL_1) == value


@pytest.mark.parametrize("method", ["get", "exists", "remove"])
@pytest.mark.parametrize("invalid", [None, GOAL_1.value, PROFILE_1, RecordId("goal"), {}])
def test_goal_repository_rejects_wrong_goal_identifier_types(
    tmp_path: Path, method: str, invalid: object
) -> None:
    repository = SQLiteGoalRepository(tmp_path / "goals.sqlite3")
    with pytest.raises(TypeError):
        getattr(repository, method)(invalid)


def test_goal_repository_rejects_invalid_save_and_profile_filter_arguments(tmp_path: Path) -> None:
    repository = SQLiteGoalRepository(tmp_path / "goals.sqlite3")
    with pytest.raises(TypeError):
        repository.save({})  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        repository.list_for_profile(PROFILE_1.value)  # type: ignore[arg-type]
    assert repository.list_all() == ()


@pytest.mark.parametrize("record", all_records())
def test_record_repository_round_trips_every_exact_record_across_instances(
    tmp_path: Path, record: object
) -> None:
    database = tmp_path / f"{record.metadata.record_id.value}.sqlite3"  # type: ignore[attr-defined]
    SQLiteWellnessRecordRepository(database).save(PROFILE_1, record)  # type: ignore[arg-type]
    reconstructed = SQLiteWellnessRecordRepository(database).get(
        PROFILE_1,
        record.metadata.record_id,  # type: ignore[attr-defined]
    )

    assert reconstructed == record
    assert reconstructed is not record
    assert type(reconstructed) is type(record)


def test_record_repository_composite_ownership_upsert_and_type_replacement(tmp_path: Path) -> None:
    database = tmp_path / "records.sqlite3"
    repository = SQLiteWellnessRecordRepository(database)
    first = hydration("shared", 200)
    other_profile = hydration("shared", 300)
    replacement = MealRecord(metadata("shared"), MealType.LUNCH, MealNutrition(calories_kcal=600))
    repository.save(PROFILE_1, first)
    repository.save(PROFILE_2, other_profile)
    repository.save(PROFILE_1, replacement)

    reopened = SQLiteWellnessRecordRepository(database)
    assert reopened.get(PROFILE_1, RecordId("shared")) == replacement
    assert reopened.get(PROFILE_2, RecordId("shared")) == other_profile
    assert reopened.list_by_type(PROFILE_1, HydrationRecord) == ()
    assert reopened.list_by_type(PROFILE_1, MealRecord) == (replacement,)
    reopened.remove(PROFILE_1, RecordId("shared"))
    assert reopened.get(PROFILE_2, RecordId("shared")) == other_profile
    with pytest.raises(EntityNotFoundError):
        reopened.remove(PROFILE_1, RecordId("shared"))


def test_record_ordering_uses_epoch_across_offsets_then_identifier(tmp_path: Path) -> None:
    repository = SQLiteWellnessRecordRepository(tmp_path / "ordering.sqlite3")
    earliest = hydration(
        "z-earliest",
        observed_at=datetime(2026, 10, 1, 9, tzinfo=timezone(timedelta(hours=5, minutes=30))),
    )
    same_first = hydration(
        "a-same",
        observed_at=datetime(2026, 10, 1, 4, tzinfo=UTC),
    )
    same_second = hydration(
        "b-same",
        observed_at=datetime(2026, 9, 30, 23, tzinfo=timezone(timedelta(hours=-5))),
    )
    latest = hydration(
        "a-latest",
        observed_at=datetime(2026, 10, 1, 6, tzinfo=UTC),
    )
    for record in (latest, same_second, earliest, same_first):
        repository.save(PROFILE_1, record)

    assert repository.list_for_profile(PROFILE_1) == (
        earliest,
        same_first,
        same_second,
        latest,
    )


def test_record_time_range_boundaries_and_exact_type_filtering(tmp_path: Path) -> None:
    repository = SQLiteWellnessRecordRepository(tmp_path / "filtering.sqlite3")
    start = BASE_TIME
    end = BASE_TIME + timedelta(hours=2)
    before = hydration("before", observed_at=start - timedelta(seconds=1))
    at_start = hydration("start", observed_at=start)
    inside = hydration("inside", observed_at=start + timedelta(hours=1))
    other_type = MealRecord(
        metadata("meal", observed_at=start + timedelta(minutes=30)),
        MealType.LUNCH,
        MealNutrition(calories_kcal=500),
    )
    at_end = hydration("end", observed_at=end)
    after = hydration("after", observed_at=end + timedelta(seconds=1))
    for record in (after, at_end, other_type, inside, at_start, before):
        repository.save(PROFILE_1, record)
    requested = TimeRange(start, end)

    assert repository.list_in_time_range(PROFILE_1, requested) == (at_start, other_type, inside)
    assert repository.list_by_type(PROFILE_1, HydrationRecord) == (
        before,
        at_start,
        inside,
        at_end,
        after,
    )
    assert repository.list_by_type_in_time_range(PROFILE_1, HydrationRecord, requested) == (
        at_start,
        inside,
    )


def test_record_repository_empty_exists_missing_and_wrong_arguments(tmp_path: Path) -> None:
    repository = SQLiteWellnessRecordRepository(tmp_path / "records.sqlite3")
    assert repository.list_for_profile(PROFILE_1) == ()
    assert repository.exists(PROFILE_1, RecordId("missing")) is False
    with pytest.raises(EntityNotFoundError):
        repository.get(PROFILE_1, RecordId("missing"))
    with pytest.raises(EntityNotFoundError):
        repository.remove(PROFILE_1, RecordId("missing"))
    for invalid in (None, PROFILE_1.value, GOAL_1, RecordId("profile"), {}):
        with pytest.raises(TypeError):
            repository.list_for_profile(invalid)  # type: ignore[arg-type]
    for invalid in (None, "record", PROFILE_1, GOAL_1, {}):
        with pytest.raises(TypeError):
            repository.get(PROFILE_1, invalid)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        repository.list_in_time_range(PROFILE_1, "range")  # type: ignore[arg-type]


def test_record_repository_rejects_invalid_objects_classes_and_subclasses(tmp_path: Path) -> None:
    class UnsupportedHydration(HydrationRecord):
        pass

    repository = SQLiteWellnessRecordRepository(tmp_path / "records.sqlite3")
    unsupported = UnsupportedHydration(metadata("unsupported"), 250)
    for invalid in (None, object(), {}, unsupported):
        with pytest.raises(TypeError):
            repository.save(PROFILE_1, invalid)  # type: ignore[arg-type]
    for invalid in (None, object, unsupported):
        with pytest.raises(TypeError):
            repository.list_by_type(PROFILE_1, invalid)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        repository.list_by_type(PROFILE_1, UnsupportedHydration)  # type: ignore[arg-type]
    assert repository.list_for_profile(PROFILE_1) == ()


def test_profile_removal_does_not_cascade_goals_or_records(tmp_path: Path) -> None:
    database = tmp_path / "no-cascade.sqlite3"
    profiles = SQLiteProfileRepository(database)
    goals = SQLiteGoalRepository(database)
    records = SQLiteWellnessRecordRepository(database)
    profiles.save(profile(PROFILE_1))
    goals.save(goal(GOAL_1, PROFILE_1))
    value = hydration("record")
    records.save(PROFILE_1, value)

    profiles.remove(PROFILE_1)

    assert goals.get(GOAL_1) == goal(GOAL_1, PROFILE_1)
    assert records.get(PROFILE_1, RecordId("record")) == value


@pytest.mark.parametrize(
    ("table", "key_value", "corruption"),
    [
        ("wellness_profiles", PROFILE_1.value, "not-json"),
        ("wellness_goals", GOAL_1.value, "not-json"),
    ],
)
def test_corrupt_profile_and_goal_payloads_raise_persistence_errors_with_chaining(
    tmp_path: Path,
    table: str,
    key_value: str,
    corruption: str,
) -> None:
    database = tmp_path / f"{table}.sqlite3"
    profiles = SQLiteProfileRepository(database)
    goals = SQLiteGoalRepository(database)
    profiles.save(profile(PROFILE_1))
    goals.save(goal(GOAL_1, PROFILE_1))
    with connect(database) as connection:
        if table == "wellness_profiles":
            connection.execute(
                "UPDATE wellness_profiles SET payload = ? WHERE profile_id = ?",
                (corruption, key_value),
            )
        else:
            connection.execute(
                "UPDATE wellness_goals SET payload = ? WHERE goal_id = ?",
                (corruption, key_value),
            )
    action = profiles.get if table == "wellness_profiles" else goals.get
    identifier = PROFILE_1 if table == "wellness_profiles" else GOAL_1
    with pytest.raises(RepositoryPersistenceError) as caught:
        action(identifier)  # type: ignore[arg-type]
    assert caught.value.__cause__ is not None


@pytest.mark.parametrize("corruption", ["unknown-type", "invalid-json", "wrong-entity", "bad-time"])
def test_corrupt_record_rows_raise_persistence_errors_without_repair(
    tmp_path: Path, corruption: str
) -> None:
    database = tmp_path / f"record-{corruption}.sqlite3"
    repository = SQLiteWellnessRecordRepository(database)
    value = hydration("record")
    repository.save(PROFILE_1, value)
    with connect(database) as connection:
        if corruption == "unknown-type":
            connection.execute("UPDATE wellness_records SET record_type = ?", ("unknown",))
        elif corruption == "invalid-json":
            connection.execute("UPDATE wellness_records SET payload = ?", ("not-json",))
        else:
            row = connection.execute("SELECT payload FROM wellness_records").fetchone()
            payload = json.loads(row["payload"])
            if corruption == "wrong-entity":
                payload["entity_type"] = "MealRecord"
            else:
                payload["data"]["metadata"]["recorded_at"] = "not-a-time"
            connection.execute(
                "UPDATE wellness_records SET payload = ?",
                (json.dumps(payload),),
            )
    with pytest.raises(RepositoryPersistenceError) as caught:
        repository.get(PROFILE_1, RecordId("record"))
    assert caught.value.__cause__ is not None
    assert repository.exists(PROFILE_1, RecordId("record")) is True


def test_failed_remove_rolls_back_and_preserves_unrelated_rows(tmp_path: Path) -> None:
    database = tmp_path / "rollback.sqlite3"
    repository = SQLiteProfileRepository(database)
    second = profile(PROFILE_2)
    repository.save(second)
    with pytest.raises(EntityNotFoundError):
        repository.remove(PROFILE_1)
    assert SQLiteProfileRepository(database).get(PROFILE_2) == second


def test_existing_application_services_and_summary_workflow_use_reopened_sqlite_repositories(
    tmp_path: Path,
) -> None:
    database = tmp_path / "application.sqlite3"
    profiles = SQLiteProfileRepository(database)
    goals = SQLiteGoalRepository(database)
    records = SQLiteWellnessRecordRepository(database)
    stored_profile = profile(PROFILE_1)
    stored_goal = goal(GOAL_1, PROFILE_1)
    ProfileService(profiles).save_profile(stored_profile)
    GoalService(profiles, goals).save_goal(stored_goal)
    record_service = WellnessRecordService(profiles, records)
    record_service.save_record(PROFILE_1, hydration("first", 200, observed_at=BASE_TIME))
    record_service.save_record(
        PROFILE_1,
        hydration("second", 300, observed_at=BASE_TIME + timedelta(days=1)),
    )

    reopened_profiles = SQLiteProfileRepository(database)
    reopened_goals = SQLiteGoalRepository(database)
    reopened_records = SQLiteWellnessRecordRepository(database)
    summary = WellnessSummaryService(reopened_profiles, reopened_records).create_summary(PROFILE_1)

    assert ProfileService(reopened_profiles).get_profile(PROFILE_1) == stored_profile
    assert GoalService(reopened_profiles, reopened_goals).list_goals_for_profile(PROFILE_1) == (
        stored_goal,
    )
    assert (
        len(
            WellnessRecordService(reopened_profiles, reopened_records).list_records_for_profile(
                PROFILE_1
            )
        )
        == 2
    )
    assert summary.generated_from_record_count == 2
    assert summary.metrics[0].metric is MetricIdentifier.WATER_INTAKE
    assert summary.metrics[0].trend is not None
