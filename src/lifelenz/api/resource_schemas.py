"""Strict transport schemas for authenticated profile and wellness-record resources."""

from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt

from lifelenz.domain import (
    BeverageType,
    CheckInTag,
    CycleSymptom,
    DataSource,
    MealType,
    MeasurementSystem,
    MenstrualFlow,
    MoodCategory,
    SleepQuality,
    SymptomIntensity,
    TrackedWellnessDomain,
    WeekStart,
    WorkoutType,
)


class _StrictResourceModel(BaseModel):
    # FastAPI supplies already-decoded JSON values to Pydantic. Dates, datetimes,
    # enum strings, and JSON arrays therefore need transport-aware parsing, while
    # numeric fields remain strict to reject numeric strings.
    model_config = ConfigDict(extra="forbid", frozen=True)


class WellnessProfileRequest(_StrictResourceModel):
    time_zone: str
    display_name: str | None = None
    measurement_system: MeasurementSystem = MeasurementSystem.METRIC
    week_start: WeekStart = WeekStart.MONDAY
    tracked_domains: tuple[TrackedWellnessDomain, ...] = ()


class WellnessProfileResponse(WellnessProfileRequest):
    profile_id: UUID


class RecordMetadataRequest(_StrictResourceModel):
    recorded_at: datetime
    source: DataSource
    notes: str | None = None


class RecordMetadataResponse(RecordMetadataRequest):
    record_id: str


class TimeRangeData(_StrictResourceModel):
    start: datetime
    end: datetime


class SleepStageData(_StrictResourceModel):
    awake_minutes: StrictFloat = 0.0
    light_minutes: StrictFloat = 0.0
    deep_minutes: StrictFloat = 0.0
    rem_minutes: StrictFloat = 0.0


class MealNutritionData(_StrictResourceModel):
    calories_kcal: StrictFloat | None = None
    protein_grams: StrictFloat | None = None
    carbohydrates_grams: StrictFloat | None = None
    fat_grams: StrictFloat | None = None
    fibre_grams: StrictFloat | None = None


class CycleSymptomData(_StrictResourceModel):
    symptom: CycleSymptom
    intensity: SymptomIntensity | None = None


class SleepData(_StrictResourceModel):
    period: TimeRangeData
    sleep_minutes: StrictFloat
    awake_minutes: StrictFloat
    quality: SleepQuality | None = None
    stages: SleepStageData | None = None
    interruption_count: StrictInt | None = None


class DailyActivityData(_StrictResourceModel):
    activity_date: date
    steps: StrictInt = 0
    distance_kilometers: StrictFloat = 0.0
    active_minutes: StrictFloat = 0.0
    active_calories_kcal: StrictFloat = 0.0


class WorkoutData(_StrictResourceModel):
    period: TimeRangeData
    workout_type: WorkoutType
    distance_kilometers: StrictFloat | None = None
    active_calories_kcal: StrictFloat | None = None
    perceived_exertion: StrictInt | None = None
    average_heart_rate_bpm: StrictFloat | None = None


class HydrationData(_StrictResourceModel):
    volume_milliliters: StrictFloat
    beverage_type: BeverageType = BeverageType.WATER
    caffeine_milligrams: StrictFloat | None = None


class MealData(_StrictResourceModel):
    meal_type: MealType
    nutrition: MealNutritionData
    name: str | None = None


class DailyNutritionData(_StrictResourceModel):
    nutrition_date: date
    nutrition: MealNutritionData
    meal_count: StrictInt | None = None


class BodyMeasurementData(_StrictResourceModel):
    weight_kilograms: StrictFloat
    height_meters: StrictFloat | None = None
    body_fat_percent: StrictFloat | None = None
    waist_circumference_centimeters: StrictFloat | None = None


class SubjectiveCheckInData(_StrictResourceModel):
    mood_score: StrictInt
    energy_score: StrictInt
    stress_score: StrictInt
    motivation_score: StrictInt | None = None
    mood_category: MoodCategory | None = None
    tags: tuple[CheckInTag, ...] = ()


class MenstrualBleedingData(_StrictResourceModel):
    flow: MenstrualFlow
    symptoms: tuple[CycleSymptomData, ...] = ()


class MenstrualCycleData(_StrictResourceModel):
    start_date: date
    end_date: date | None = None


class SleepRecordRequest(_StrictResourceModel):
    record_type: Literal["sleep"]
    metadata: RecordMetadataRequest
    data: SleepData


class DailyActivityRecordRequest(_StrictResourceModel):
    record_type: Literal["daily_activity"]
    metadata: RecordMetadataRequest
    data: DailyActivityData


class WorkoutRecordRequest(_StrictResourceModel):
    record_type: Literal["workout"]
    metadata: RecordMetadataRequest
    data: WorkoutData


class HydrationRecordRequest(_StrictResourceModel):
    record_type: Literal["hydration"]
    metadata: RecordMetadataRequest
    data: HydrationData


class MealRecordRequest(_StrictResourceModel):
    record_type: Literal["meal"]
    metadata: RecordMetadataRequest
    data: MealData


class DailyNutritionRecordRequest(_StrictResourceModel):
    record_type: Literal["daily_nutrition"]
    metadata: RecordMetadataRequest
    data: DailyNutritionData


class BodyMeasurementRecordRequest(_StrictResourceModel):
    record_type: Literal["body_measurement"]
    metadata: RecordMetadataRequest
    data: BodyMeasurementData


class SubjectiveCheckInRecordRequest(_StrictResourceModel):
    record_type: Literal["subjective_check_in"]
    metadata: RecordMetadataRequest
    data: SubjectiveCheckInData


class MenstrualBleedingRecordRequest(_StrictResourceModel):
    record_type: Literal["menstrual_bleeding"]
    metadata: RecordMetadataRequest
    data: MenstrualBleedingData


class MenstrualCycleRecordRequest(_StrictResourceModel):
    record_type: Literal["menstrual_cycle"]
    metadata: RecordMetadataRequest
    data: MenstrualCycleData


WellnessRecordTypeName = Literal[
    "sleep",
    "daily_activity",
    "workout",
    "hydration",
    "meal",
    "daily_nutrition",
    "body_measurement",
    "subjective_check_in",
    "menstrual_bleeding",
    "menstrual_cycle",
]


WellnessRecordCreateRequest = Annotated[
    SleepRecordRequest
    | DailyActivityRecordRequest
    | WorkoutRecordRequest
    | HydrationRecordRequest
    | MealRecordRequest
    | DailyNutritionRecordRequest
    | BodyMeasurementRecordRequest
    | SubjectiveCheckInRecordRequest
    | MenstrualBleedingRecordRequest
    | MenstrualCycleRecordRequest,
    Field(discriminator="record_type"),
]

WellnessRecordData = (
    SleepData
    | DailyActivityData
    | WorkoutData
    | HydrationData
    | MealData
    | DailyNutritionData
    | BodyMeasurementData
    | SubjectiveCheckInData
    | MenstrualBleedingData
    | MenstrualCycleData
)


class WellnessRecordResponse(_StrictResourceModel):
    record_type: WellnessRecordTypeName
    metadata: RecordMetadataResponse
    data: WellnessRecordData
