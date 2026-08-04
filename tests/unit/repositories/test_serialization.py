"""Unit tests for explicit deterministic repository JSON serialization."""

import json
from datetime import date, datetime, timedelta, timezone

import pytest

import lifelenz.repositories.serialization as serialization_module
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
from lifelenz.repositories.serialization import (
    SerializationError,
    deserialize_wellness_goal,
    deserialize_wellness_profile,
    deserialize_wellness_record,
    record_discriminator,
    serialize_wellness_goal,
    serialize_wellness_profile,
    serialize_wellness_record,
)

PROFILE_ID = ProfileId("40000000-0000-4000-8000-000000000001")
GOAL_ID = GoalId("41000000-0000-4000-8000-000000000001")
BASE_TIME = datetime(2026, 9, 1, 8, 30, 15, 123456, tzinfo=timezone(timedelta(hours=5, minutes=30)))


def metadata(record_id: str) -> RecordMetadata:
    return RecordMetadata(
        RecordId(record_id),
        BASE_TIME,
        DataSource.APP_IMPORT,
        "  Unicode note café  ",
    )


def supported_records() -> tuple[object, ...]:
    period = TimeRange(BASE_TIME - timedelta(hours=8), BASE_TIME)
    nutrition = MealNutrition(2100, 95.5, 250, 70.25, 30)
    return (
        SleepRecord(
            metadata("sleep"),
            period,
            420,
            60,
            SleepQuality.GOOD,
            SleepStageDurations(30, 220, 100, 100),
            2,
        ),
        DailyActivityRecord(metadata("activity"), date(2026, 9, 1), 12345, 8.25, 75, 456.5),
        WorkoutRecord(
            metadata("workout"),
            TimeRange(BASE_TIME - timedelta(minutes=90), BASE_TIME),
            WorkoutType.CYCLING,
            32.5,
            650,
            PerceivedExertion(8),
            148.5,
        ),
        HydrationRecord(metadata("hydration"), 355.5, BeverageType.COFFEE, 95),
        MealRecord(metadata("meal"), MealType.DINNER, nutrition, "  Déjeuner spécial  "),
        DailyNutritionRecord(metadata("nutrition"), date(2026, 9, 1), nutrition, 4),
        BodyMeasurementRecord(metadata("body"), 72.25, 1.78, 18.5, 82),
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
            MenstrualFlow.MODERATE,
            (
                CycleSymptomEntry(CycleSymptom.CRAMPS, SymptomIntensity.MILD),
                CycleSymptomEntry(CycleSymptom.FATIGUE),
            ),
        ),
        MenstrualCycleRecord(metadata("cycle"), date(2026, 8, 28), date(2026, 9, 2)),
    )


def mutate_payload(payload: str, mutation: object) -> str:
    value = json.loads(payload)
    mutation(value)  # type: ignore[operator]
    return json.dumps(value)


@pytest.mark.parametrize(
    "profile",
    [
        WellnessProfile(PROFILE_ID, "UTC"),
        WellnessProfile(
            PROFILE_ID,
            "Asia/Kolkata",
            display_name="  Zoë 東京  ",
            measurement_system=MeasurementSystem.IMPERIAL,
            week_start=WeekStart.SUNDAY,
            tracked_domains=(
                TrackedWellnessDomain.SLEEP,
                TrackedWellnessDomain.HYDRATION,
                TrackedWellnessDomain.MENSTRUAL_CYCLE,
            ),
        ),
        WellnessProfile(PROFILE_ID, "UTC", display_name="   "),
    ],
)
def test_profile_serialization_is_deterministic_strict_and_round_trips(
    profile: WellnessProfile,
) -> None:
    first = serialize_wellness_profile(profile)
    second = serialize_wellness_profile(profile)
    envelope = json.loads(first)
    reconstructed = deserialize_wellness_profile(first)

    assert first == second
    assert first == json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert envelope["schema_version"] == 1
    assert envelope["entity_type"] == "WellnessProfile"
    assert reconstructed == profile
    assert hash(reconstructed) == hash(profile)
    assert "Zoë 東京" in first if profile.display_name else True


@pytest.mark.parametrize("direction", tuple(GoalDirection))
@pytest.mark.parametrize("status", tuple(GoalStatus))
def test_goal_serialization_preserves_every_direction_status_and_nested_value(
    direction: GoalDirection,
    status: GoalStatus,
) -> None:
    goal = WellnessGoal(
        GOAL_ID,
        PROFILE_ID,
        GoalTarget(MetricIdentifier.WEIGHT, 72.5, MeasurementUnit.KILOGRAMS),
        direction,
        status,
        date(2026, 9, 1),
        date(2026, 12, 31),
        "  Objetivo 東京  ",
        "  Line one\nLine two  ",
    )
    reconstructed = deserialize_wellness_goal(serialize_wellness_goal(goal))

    assert reconstructed == goal
    assert hash(reconstructed) == hash(goal)


@pytest.mark.parametrize("value", [0, 1000, 12.75])
@pytest.mark.parametrize(
    ("start_date", "target_date"),
    [(None, None), (date(2026, 1, 1), None), (None, date(2026, 2, 1))],
)
def test_goal_serialization_preserves_numeric_types_and_optional_dates(
    value: int | float,
    start_date: date | None,
    target_date: date | None,
) -> None:
    goal = WellnessGoal(
        GOAL_ID,
        PROFILE_ID,
        GoalTarget(MetricIdentifier.STEPS, value, MeasurementUnit.COUNT),
        GoalDirection.AT_LEAST,
        start_date=start_date,
        target_date=target_date,
    )
    reconstructed = deserialize_wellness_goal(serialize_wellness_goal(goal))

    assert reconstructed == goal
    assert type(reconstructed.target.value) is type(value)


@pytest.mark.parametrize(
    ("record", "expected_discriminator"),
    tuple(
        zip(
            supported_records(),
            (
                "sleep",
                "daily_activity",
                "workout",
                "hydration",
                "meal",
                "daily_nutrition",
                "body_measurement",
                "subjective_wellness_check_in",
                "menstrual_bleeding",
                "menstrual_cycle",
            ),
            strict=True,
        )
    ),
)
def test_every_supported_record_round_trips_with_stable_discriminator(
    record: object,
    expected_discriminator: str,
) -> None:
    discriminator, payload = serialize_wellness_record(record)  # type: ignore[arg-type]
    reconstructed = deserialize_wellness_record(discriminator, payload)

    assert discriminator == expected_discriminator
    assert record_discriminator(type(record)) == expected_discriminator
    assert reconstructed == record
    assert hash(reconstructed) == hash(record)
    assert reconstructed is not record
    assert reconstructed.metadata.recorded_at.isoformat() == BASE_TIME.isoformat()


@pytest.mark.parametrize(
    "record",
    [
        SleepRecord(
            metadata("sleep-min"), TimeRange(BASE_TIME - timedelta(hours=1), BASE_TIME), 60, 0
        ),
        WorkoutRecord(
            metadata("workout-min"),
            TimeRange(BASE_TIME - timedelta(minutes=30), BASE_TIME),
            WorkoutType.WALKING,
        ),
        MealRecord(metadata("meal-min"), MealType.SNACK, MealNutrition(calories_kcal=250)),
        SubjectiveWellnessCheckIn(
            metadata("checkin-min"), SubjectiveScore(5), SubjectiveScore(5), SubjectiveScore(5)
        ),
        MenstrualBleedingRecord(metadata("bleeding-min"), MenstrualFlow.SPOTTING),
        MenstrualCycleRecord(metadata("cycle-min"), date(2026, 9, 1)),
    ],
)
def test_record_serialization_preserves_optional_none_and_empty_tuple_values(
    record: object,
) -> None:
    discriminator, payload = serialize_wellness_record(record)  # type: ignore[arg-type]
    assert deserialize_wellness_record(discriminator, payload) == record


@pytest.mark.parametrize("serializer", [serialize_wellness_profile, serialize_wellness_goal])
@pytest.mark.parametrize("invalid", [None, {}, object(), "entity"])
def test_entity_serializers_reject_wrong_types(serializer: object, invalid: object) -> None:
    with pytest.raises(TypeError):
        serializer(invalid)  # type: ignore[operator]


def test_record_serializer_and_discriminator_reject_objects_and_subclasses() -> None:
    class UnsupportedHydration(HydrationRecord):
        pass

    unsupported = UnsupportedHydration(metadata("unsupported"), 250)
    for value in (None, object(), unsupported):
        with pytest.raises(TypeError):
            serialize_wellness_record(value)  # type: ignore[arg-type]
    for value in (None, supported_records()[3], UnsupportedHydration, object):
        with pytest.raises(TypeError):
            record_discriminator(value)


@pytest.mark.parametrize(
    "payload",
    [
        "not-json",
        "[]",
        json.dumps({"entity_type": "WellnessProfile", "data": {}}),
        json.dumps({"schema_version": 2, "entity_type": "WellnessProfile", "data": {}}),
        json.dumps({"schema_version": True, "entity_type": "WellnessProfile", "data": {}}),
        json.dumps({"schema_version": 1, "data": {}}),
        json.dumps({"schema_version": 1, "entity_type": "WellnessGoal", "data": {}}),
        json.dumps({"schema_version": 1, "entity_type": "WellnessProfile", "data": []}),
        json.dumps({"schema_version": 1, "entity_type": "WellnessProfile", "data": {}, "extra": 1}),
    ],
)
def test_profile_deserializer_rejects_malformed_envelopes(payload: str) -> None:
    with pytest.raises(SerializationError):
        deserialize_wellness_profile(payload)


def test_deserializers_reject_missing_extra_and_invalid_nested_fields() -> None:
    profile_payload = serialize_wellness_profile(WellnessProfile(PROFILE_ID, "UTC"))
    with pytest.raises(SerializationError):
        deserialize_wellness_profile(
            mutate_payload(profile_payload, lambda value: value["data"].pop("profile_id"))
        )
    with pytest.raises(SerializationError):
        deserialize_wellness_profile(
            mutate_payload(profile_payload, lambda value: value["data"].update(extra=True))
        )
    with pytest.raises(SerializationError):
        deserialize_wellness_profile(
            mutate_payload(
                profile_payload, lambda value: value["data"].update(week_start="unknown")
            )
        )

    goal = WellnessGoal(
        GOAL_ID,
        PROFILE_ID,
        GoalTarget(MetricIdentifier.STEPS, 1000, MeasurementUnit.COUNT),
        GoalDirection.AT_LEAST,
    )
    goal_payload = serialize_wellness_goal(goal)
    with pytest.raises(SerializationError):
        deserialize_wellness_goal(
            mutate_payload(goal_payload, lambda value: value["data"]["target"].pop("unit"))
        )


def test_record_deserializer_rejects_unknown_mismatch_and_corrupt_nested_data() -> None:
    discriminator, payload = serialize_wellness_record(supported_records()[0])  # type: ignore[arg-type]
    with pytest.raises(SerializationError, match="unknown"):
        deserialize_wellness_record("unknown", payload)
    with pytest.raises(SerializationError, match="entity_type"):
        deserialize_wellness_record("hydration", payload)
    with pytest.raises(SerializationError):
        deserialize_wellness_record(discriminator, "{")
    with pytest.raises(SerializationError):
        deserialize_wellness_record(
            discriminator,
            mutate_payload(payload, lambda value: value["data"]["metadata"].pop("record_id")),
        )
    with pytest.raises(SerializationError):
        deserialize_wellness_record(
            discriminator,
            mutate_payload(
                payload,
                lambda value: value["data"]["metadata"].update(recorded_at="2026-01-01"),
            ),
        )
    with pytest.raises(SerializationError):
        deserialize_wellness_record(
            discriminator,
            mutate_payload(payload, lambda value: value["data"].update(quality="unknown")),
        )


def test_deserializers_reject_non_string_payload_and_record_type() -> None:
    with pytest.raises(SerializationError):
        deserialize_wellness_profile(b"payload")  # type: ignore[arg-type]
    with pytest.raises(SerializationError):
        deserialize_wellness_record(None, "{}")  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [object(), float("nan")])
def test_json_encoder_rejects_non_json_safe_values(value: object) -> None:
    with pytest.raises(SerializationError, match="serialize"):
        serialization_module._dump("Synthetic", {"value": value})


@pytest.mark.parametrize("value", [123, "not-a-date"])
def test_goal_deserializer_rejects_wrong_or_invalid_date_primitives(value: object) -> None:
    goal = WellnessGoal(
        GOAL_ID,
        PROFILE_ID,
        GoalTarget(MetricIdentifier.STEPS, 1000, MeasurementUnit.COUNT),
        GoalDirection.AT_LEAST,
        start_date=date(2026, 1, 1),
    )
    payload = mutate_payload(
        serialize_wellness_goal(goal),
        lambda envelope: envelope["data"].update(start_date=value),
    )
    with pytest.raises(SerializationError):
        deserialize_wellness_goal(payload)


@pytest.mark.parametrize("value", [123, "not-a-datetime"])
def test_record_deserializer_rejects_wrong_or_invalid_datetime_primitive(value: object) -> None:
    discriminator, payload = serialize_wellness_record(supported_records()[3])  # type: ignore[arg-type]
    malformed = mutate_payload(
        payload,
        lambda envelope: envelope["data"]["metadata"].update(recorded_at=value),
    )
    with pytest.raises(SerializationError):
        deserialize_wellness_record(discriminator, malformed)
