"""Explicit deterministic JSON serialization for repository persistence internals."""

import json
from collections.abc import Callable
from datetime import date, datetime
from typing import Any

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
from lifelenz.repositories.contracts import WellnessRecord

_PAYLOAD_SCHEMA_VERSION = 1


class SerializationError(ValueError):
    """Internal signal that an entity payload cannot be encoded or reconstructed."""


def _dump(entity_type: str, data: dict[str, object]) -> str:
    try:
        return json.dumps(
            {
                "schema_version": _PAYLOAD_SCHEMA_VERSION,
                "entity_type": entity_type,
                "data": data,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise SerializationError(f"could not serialize {entity_type}") from error


def _mapping(value: object, expected_keys: set[str], *, context: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise SerializationError(f"{context} must be a JSON object")
    actual_keys = set(value)
    if actual_keys != expected_keys:
        raise SerializationError(
            f"{context} fields must be exactly {sorted(expected_keys)!r}; got {sorted(actual_keys)!r}"
        )
    return value


def _load(payload: str, expected_entity_type: str) -> dict[str, Any]:
    if type(payload) is not str:
        raise SerializationError("payload must be a plain string")
    try:
        envelope = json.loads(payload)
    except json.JSONDecodeError as error:
        raise SerializationError("payload must contain valid JSON") from error
    envelope = _mapping(
        envelope,
        {"schema_version", "entity_type", "data"},
        context="payload envelope",
    )
    version = envelope["schema_version"]
    if type(version) is not int or version != _PAYLOAD_SCHEMA_VERSION:
        raise SerializationError(f"unsupported payload schema version {version!r}")
    if envelope["entity_type"] != expected_entity_type:
        raise SerializationError(
            f"payload entity_type must be {expected_entity_type!r}; got {envelope['entity_type']!r}"
        )
    data = envelope["data"]
    if type(data) is not dict:
        raise SerializationError("payload data must be a JSON object")
    return data


def _construct(entity_type: str, factory: Callable[[], Any]) -> Any:
    try:
        return factory()
    except SerializationError:
        raise
    except (KeyError, TypeError, ValueError) as error:
        raise SerializationError(f"could not deserialize {entity_type}") from error


def _optional(value: object, factory: Callable[[object], Any]) -> Any:
    return None if value is None else factory(value)


def _date(value: object) -> date:
    if type(value) is not str:
        raise SerializationError("date value must be a string")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise SerializationError("date value must use ISO 8601") from error


def _datetime(value: object) -> datetime:
    if type(value) is not str:
        raise SerializationError("datetime value must be a string")
    try:
        return datetime.fromisoformat(value)
    except ValueError as error:
        raise SerializationError("datetime value must use ISO 8601") from error


def _metadata_data(metadata: RecordMetadata) -> dict[str, object]:
    return {
        "record_id": metadata.record_id.value,
        "recorded_at": metadata.recorded_at.isoformat(),
        "source": metadata.source.value,
        "notes": metadata.notes,
    }


def _metadata(value: object) -> RecordMetadata:
    data = _mapping(
        value,
        {"record_id", "recorded_at", "source", "notes"},
        context="record metadata",
    )
    return RecordMetadata(
        RecordId(data["record_id"]),
        _datetime(data["recorded_at"]),
        DataSource(data["source"]),
        data["notes"],
    )


def _time_range_data(value: TimeRange) -> dict[str, str]:
    return {"start": value.start.isoformat(), "end": value.end.isoformat()}


def _time_range(value: object) -> TimeRange:
    data = _mapping(value, {"start", "end"}, context="time range")
    return TimeRange(_datetime(data["start"]), _datetime(data["end"]))


def _nutrition_data(value: MealNutrition) -> dict[str, object]:
    return {
        "calories_kcal": value.calories_kcal,
        "protein_grams": value.protein_grams,
        "carbohydrates_grams": value.carbohydrates_grams,
        "fat_grams": value.fat_grams,
        "fibre_grams": value.fibre_grams,
    }


def _nutrition(value: object) -> MealNutrition:
    data = _mapping(
        value,
        {
            "calories_kcal",
            "protein_grams",
            "carbohydrates_grams",
            "fat_grams",
            "fibre_grams",
        },
        context="meal nutrition",
    )
    return MealNutrition(**data)


def serialize_wellness_profile(profile: WellnessProfile) -> str:
    """Return deterministic versioned JSON for one exact wellness profile."""
    if type(profile) is not WellnessProfile:
        raise TypeError(f"profile must be an exact WellnessProfile; got {profile!r}")
    return _dump(
        "WellnessProfile",
        {
            "profile_id": profile.profile_id.value,
            "time_zone": profile.time_zone,
            "display_name": profile.display_name,
            "measurement_system": profile.measurement_system.value,
            "week_start": profile.week_start.value,
            "tracked_domains": [item.value for item in profile.tracked_domains],
        },
    )


def deserialize_wellness_profile(payload: str) -> WellnessProfile:
    """Reconstruct a wellness profile through its public constructor."""
    data = _mapping(
        _load(payload, "WellnessProfile"),
        {
            "profile_id",
            "time_zone",
            "display_name",
            "measurement_system",
            "week_start",
            "tracked_domains",
        },
        context="WellnessProfile data",
    )
    return _construct(
        "WellnessProfile",
        lambda: WellnessProfile(
            profile_id=ProfileId(data["profile_id"]),
            time_zone=data["time_zone"],
            display_name=data["display_name"],
            measurement_system=MeasurementSystem(data["measurement_system"]),
            week_start=WeekStart(data["week_start"]),
            tracked_domains=tuple(TrackedWellnessDomain(item) for item in data["tracked_domains"]),
        ),
    )


def serialize_wellness_goal(goal: WellnessGoal) -> str:
    """Return deterministic versioned JSON for one exact wellness goal."""
    if type(goal) is not WellnessGoal:
        raise TypeError(f"goal must be an exact WellnessGoal; got {goal!r}")
    return _dump(
        "WellnessGoal",
        {
            "goal_id": goal.goal_id.value,
            "profile_id": goal.profile_id.value,
            "target": {
                "metric": goal.target.metric.value,
                "value": goal.target.value,
                "unit": goal.target.unit.value,
            },
            "direction": goal.direction.value,
            "status": goal.status.value,
            "start_date": None if goal.start_date is None else goal.start_date.isoformat(),
            "target_date": None if goal.target_date is None else goal.target_date.isoformat(),
            "title": goal.title,
            "description": goal.description,
        },
    )


def deserialize_wellness_goal(payload: str) -> WellnessGoal:
    """Reconstruct a wellness goal through its public constructors."""
    data = _mapping(
        _load(payload, "WellnessGoal"),
        {
            "goal_id",
            "profile_id",
            "target",
            "direction",
            "status",
            "start_date",
            "target_date",
            "title",
            "description",
        },
        context="WellnessGoal data",
    )
    target = _mapping(data["target"], {"metric", "value", "unit"}, context="goal target")
    return _construct(
        "WellnessGoal",
        lambda: WellnessGoal(
            goal_id=GoalId(data["goal_id"]),
            profile_id=ProfileId(data["profile_id"]),
            target=GoalTarget(
                MetricIdentifier(target["metric"]),
                target["value"],
                MeasurementUnit(target["unit"]),
            ),
            direction=GoalDirection(data["direction"]),
            status=GoalStatus(data["status"]),
            start_date=_optional(data["start_date"], _date),
            target_date=_optional(data["target_date"], _date),
            title=data["title"],
            description=data["description"],
        ),
    )


def _sleep_data(record: SleepRecord) -> dict[str, object]:
    stages = record.stages
    return {
        "metadata": _metadata_data(record.metadata),
        "period": _time_range_data(record.period),
        "sleep_minutes": record.sleep_minutes,
        "awake_minutes": record.awake_minutes,
        "quality": None if record.quality is None else record.quality.value,
        "stages": None
        if stages is None
        else {
            "awake_minutes": stages.awake_minutes,
            "light_minutes": stages.light_minutes,
            "deep_minutes": stages.deep_minutes,
            "rem_minutes": stages.rem_minutes,
        },
        "interruption_count": record.interruption_count,
    }


def _sleep(data: dict[str, Any]) -> SleepRecord:
    data = _mapping(
        data,
        {
            "metadata",
            "period",
            "sleep_minutes",
            "awake_minutes",
            "quality",
            "stages",
            "interruption_count",
        },
        context="SleepRecord data",
    )
    stages_data = data["stages"]
    stages = None
    if stages_data is not None:
        stages_data = _mapping(
            stages_data,
            {"awake_minutes", "light_minutes", "deep_minutes", "rem_minutes"},
            context="sleep stages",
        )
        stages = SleepStageDurations(**stages_data)
    return SleepRecord(
        _metadata(data["metadata"]),
        _time_range(data["period"]),
        data["sleep_minutes"],
        data["awake_minutes"],
        _optional(data["quality"], SleepQuality),
        stages,
        data["interruption_count"],
    )


def _activity_data(record: DailyActivityRecord) -> dict[str, object]:
    return {
        "metadata": _metadata_data(record.metadata),
        "activity_date": record.activity_date.isoformat(),
        "steps": record.steps,
        "distance_kilometers": record.distance_kilometers,
        "active_minutes": record.active_minutes,
        "active_calories_kcal": record.active_calories_kcal,
    }


def _activity(data: dict[str, Any]) -> DailyActivityRecord:
    data = _mapping(
        data,
        {
            "metadata",
            "activity_date",
            "steps",
            "distance_kilometers",
            "active_minutes",
            "active_calories_kcal",
        },
        context="DailyActivityRecord data",
    )
    return DailyActivityRecord(
        _metadata(data["metadata"]),
        _date(data["activity_date"]),
        data["steps"],
        data["distance_kilometers"],
        data["active_minutes"],
        data["active_calories_kcal"],
    )


def _workout_data(record: WorkoutRecord) -> dict[str, object]:
    return {
        "metadata": _metadata_data(record.metadata),
        "period": _time_range_data(record.period),
        "workout_type": record.workout_type.value,
        "distance_kilometers": record.distance_kilometers,
        "active_calories_kcal": record.active_calories_kcal,
        "perceived_exertion": None
        if record.perceived_exertion is None
        else record.perceived_exertion.score,
        "average_heart_rate_bpm": record.average_heart_rate_bpm,
    }


def _workout(data: dict[str, Any]) -> WorkoutRecord:
    data = _mapping(
        data,
        {
            "metadata",
            "period",
            "workout_type",
            "distance_kilometers",
            "active_calories_kcal",
            "perceived_exertion",
            "average_heart_rate_bpm",
        },
        context="WorkoutRecord data",
    )
    return WorkoutRecord(
        _metadata(data["metadata"]),
        _time_range(data["period"]),
        WorkoutType(data["workout_type"]),
        data["distance_kilometers"],
        data["active_calories_kcal"],
        _optional(data["perceived_exertion"], PerceivedExertion),
        data["average_heart_rate_bpm"],
    )


def _hydration_data(record: HydrationRecord) -> dict[str, object]:
    return {
        "metadata": _metadata_data(record.metadata),
        "volume_milliliters": record.volume_milliliters,
        "beverage_type": record.beverage_type.value,
        "caffeine_milligrams": record.caffeine_milligrams,
    }


def _hydration(data: dict[str, Any]) -> HydrationRecord:
    data = _mapping(
        data,
        {"metadata", "volume_milliliters", "beverage_type", "caffeine_milligrams"},
        context="HydrationRecord data",
    )
    return HydrationRecord(
        _metadata(data["metadata"]),
        data["volume_milliliters"],
        BeverageType(data["beverage_type"]),
        data["caffeine_milligrams"],
    )


def _meal_data(record: MealRecord) -> dict[str, object]:
    return {
        "metadata": _metadata_data(record.metadata),
        "meal_type": record.meal_type.value,
        "nutrition": _nutrition_data(record.nutrition),
        "name": record.name,
    }


def _meal(data: dict[str, Any]) -> MealRecord:
    data = _mapping(
        data,
        {"metadata", "meal_type", "nutrition", "name"},
        context="MealRecord data",
    )
    return MealRecord(
        _metadata(data["metadata"]),
        MealType(data["meal_type"]),
        _nutrition(data["nutrition"]),
        data["name"],
    )


def _daily_nutrition_data(record: DailyNutritionRecord) -> dict[str, object]:
    return {
        "metadata": _metadata_data(record.metadata),
        "nutrition_date": record.nutrition_date.isoformat(),
        "nutrition": _nutrition_data(record.nutrition),
        "meal_count": record.meal_count,
    }


def _daily_nutrition(data: dict[str, Any]) -> DailyNutritionRecord:
    data = _mapping(
        data,
        {"metadata", "nutrition_date", "nutrition", "meal_count"},
        context="DailyNutritionRecord data",
    )
    return DailyNutritionRecord(
        _metadata(data["metadata"]),
        _date(data["nutrition_date"]),
        _nutrition(data["nutrition"]),
        data["meal_count"],
    )


def _body_data(record: BodyMeasurementRecord) -> dict[str, object]:
    return {
        "metadata": _metadata_data(record.metadata),
        "weight_kilograms": record.weight_kilograms,
        "height_meters": record.height_meters,
        "body_fat_percent": record.body_fat_percent,
        "waist_circumference_centimeters": record.waist_circumference_centimeters,
    }


def _body(data: dict[str, Any]) -> BodyMeasurementRecord:
    data = _mapping(
        data,
        {
            "metadata",
            "weight_kilograms",
            "height_meters",
            "body_fat_percent",
            "waist_circumference_centimeters",
        },
        context="BodyMeasurementRecord data",
    )
    return BodyMeasurementRecord(
        _metadata(data["metadata"]),
        data["weight_kilograms"],
        data["height_meters"],
        data["body_fat_percent"],
        data["waist_circumference_centimeters"],
    )


def _checkin_data(record: SubjectiveWellnessCheckIn) -> dict[str, object]:
    return {
        "metadata": _metadata_data(record.metadata),
        "mood_score": record.mood_score.value,
        "energy_score": record.energy_score.value,
        "stress_score": record.stress_score.value,
        "motivation_score": None
        if record.motivation_score is None
        else record.motivation_score.value,
        "mood_category": None if record.mood_category is None else record.mood_category.value,
        "tags": [tag.value for tag in record.tags],
    }


def _checkin(data: dict[str, Any]) -> SubjectiveWellnessCheckIn:
    data = _mapping(
        data,
        {
            "metadata",
            "mood_score",
            "energy_score",
            "stress_score",
            "motivation_score",
            "mood_category",
            "tags",
        },
        context="SubjectiveWellnessCheckIn data",
    )
    return SubjectiveWellnessCheckIn(
        _metadata(data["metadata"]),
        SubjectiveScore(data["mood_score"]),
        SubjectiveScore(data["energy_score"]),
        SubjectiveScore(data["stress_score"]),
        _optional(data["motivation_score"], SubjectiveScore),
        _optional(data["mood_category"], MoodCategory),
        tuple(CheckInTag(tag) for tag in data["tags"]),
    )


def _bleeding_data(record: MenstrualBleedingRecord) -> dict[str, object]:
    return {
        "metadata": _metadata_data(record.metadata),
        "flow": record.flow.value,
        "symptoms": [
            {
                "symptom": entry.symptom.value,
                "intensity": None if entry.intensity is None else entry.intensity.value,
            }
            for entry in record.symptoms
        ],
    }


def _bleeding(data: dict[str, Any]) -> MenstrualBleedingRecord:
    data = _mapping(
        data,
        {"metadata", "flow", "symptoms"},
        context="MenstrualBleedingRecord data",
    )
    symptoms = tuple(
        CycleSymptomEntry(
            CycleSymptom(item["symptom"]),
            _optional(item["intensity"], SymptomIntensity),
        )
        for item in (
            _mapping(value, {"symptom", "intensity"}, context="cycle symptom")
            for value in data["symptoms"]
        )
    )
    return MenstrualBleedingRecord(
        _metadata(data["metadata"]),
        MenstrualFlow(data["flow"]),
        symptoms,
    )


def _cycle_data(record: MenstrualCycleRecord) -> dict[str, object]:
    return {
        "metadata": _metadata_data(record.metadata),
        "start_date": record.start_date.isoformat(),
        "end_date": None if record.end_date is None else record.end_date.isoformat(),
    }


def _cycle(data: dict[str, Any]) -> MenstrualCycleRecord:
    data = _mapping(
        data,
        {"metadata", "start_date", "end_date"},
        context="MenstrualCycleRecord data",
    )
    return MenstrualCycleRecord(
        _metadata(data["metadata"]),
        _date(data["start_date"]),
        _optional(data["end_date"], _date),
    )


_RECORD_SERIALIZERS: dict[type[WellnessRecord], tuple[str, Callable[[Any], dict[str, object]]]] = {
    SleepRecord: ("sleep", _sleep_data),
    DailyActivityRecord: ("daily_activity", _activity_data),
    WorkoutRecord: ("workout", _workout_data),
    HydrationRecord: ("hydration", _hydration_data),
    MealRecord: ("meal", _meal_data),
    DailyNutritionRecord: ("daily_nutrition", _daily_nutrition_data),
    BodyMeasurementRecord: ("body_measurement", _body_data),
    SubjectiveWellnessCheckIn: ("subjective_wellness_check_in", _checkin_data),
    MenstrualBleedingRecord: ("menstrual_bleeding", _bleeding_data),
    MenstrualCycleRecord: ("menstrual_cycle", _cycle_data),
}

_RECORD_DESERIALIZERS: dict[str, tuple[str, Callable[[dict[str, Any]], WellnessRecord]]] = {
    "sleep": ("SleepRecord", _sleep),
    "daily_activity": ("DailyActivityRecord", _activity),
    "workout": ("WorkoutRecord", _workout),
    "hydration": ("HydrationRecord", _hydration),
    "meal": ("MealRecord", _meal),
    "daily_nutrition": ("DailyNutritionRecord", _daily_nutrition),
    "body_measurement": ("BodyMeasurementRecord", _body),
    "subjective_wellness_check_in": ("SubjectiveWellnessCheckIn", _checkin),
    "menstrual_bleeding": ("MenstrualBleedingRecord", _bleeding),
    "menstrual_cycle": ("MenstrualCycleRecord", _cycle),
}


def serialize_wellness_record(record: WellnessRecord) -> tuple[str, str]:
    """Return the stable discriminator and deterministic JSON for an exact record."""
    try:
        discriminator, serializer = _RECORD_SERIALIZERS[type(record)]
    except KeyError as error:
        raise TypeError(
            f"record must be an exact supported wellness record; got {record!r}"
        ) from error
    return discriminator, _dump(type(record).__name__, serializer(record))


def deserialize_wellness_record(record_type: str, payload: str) -> WellnessRecord:
    """Reconstruct one exact supported record through public domain constructors."""
    if type(record_type) is not str:
        raise SerializationError("record_type must be a plain string")
    try:
        entity_type, deserializer = _RECORD_DESERIALIZERS[record_type]
    except KeyError as error:
        raise SerializationError(
            f"unknown wellness record discriminator {record_type!r}"
        ) from error
    data = _load(payload, entity_type)
    return _construct(entity_type, lambda: deserializer(data))


def record_discriminator(record_type: object) -> str:
    """Return the stable discriminator for an exact supported record class."""
    try:
        return _RECORD_SERIALIZERS[record_type][0]  # type: ignore[index]
    except (KeyError, TypeError) as error:
        raise TypeError(
            f"record_type must be an exact supported wellness record class; got {record_type!r}"
        ) from error
