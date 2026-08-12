"""Explicit transport mappings for wellness resources without persistence coupling."""

from uuid import UUID

from lifelenz.api.resource_schemas import (
    BodyMeasurementData,
    BodyMeasurementRecordRequest,
    CycleSymptomData,
    DailyActivityData,
    DailyActivityRecordRequest,
    DailyNutritionData,
    DailyNutritionRecordRequest,
    GoalTargetData,
    HydrationData,
    HydrationRecordRequest,
    MealData,
    MealNutritionData,
    MealRecordRequest,
    MenstrualBleedingData,
    MenstrualBleedingRecordRequest,
    MenstrualCycleData,
    MenstrualCycleRecordRequest,
    MetricWellnessSummaryResponse,
    PersonalBaselineResponse,
    RecordMetadataRequest,
    RecordMetadataResponse,
    SleepData,
    SleepRecordRequest,
    SleepStageData,
    SubjectiveCheckInData,
    SubjectiveCheckInRecordRequest,
    TimeRangeData,
    WellnessGoalRequest,
    WellnessGoalResponse,
    WellnessProfileRequest,
    WellnessProfileResponse,
    WellnessRecordCreateRequest,
    WellnessRecordResponse,
    WellnessSummaryResponse,
    WellnessTrendResponse,
    WorkoutData,
    WorkoutRecordRequest,
)
from lifelenz.application import WellnessSummary
from lifelenz.domain import (
    BodyMeasurementRecord,
    CycleSymptomEntry,
    DailyActivityRecord,
    DailyNutritionRecord,
    GoalId,
    GoalTarget,
    HydrationRecord,
    MealNutrition,
    MealRecord,
    MenstrualBleedingRecord,
    MenstrualCycleRecord,
    PerceivedExertion,
    ProfileId,
    RecordId,
    RecordMetadata,
    SleepRecord,
    SleepStageDurations,
    SubjectiveScore,
    SubjectiveWellnessCheckIn,
    TimeRange,
    WellnessGoal,
    WellnessProfile,
    WorkoutRecord,
)
from lifelenz.repositories import WellnessRecord


def profile_from_request(
    request: WellnessProfileRequest, *, profile_id: ProfileId
) -> WellnessProfile:
    return WellnessProfile(
        profile_id=profile_id,
        time_zone=request.time_zone,
        display_name=request.display_name,
        measurement_system=request.measurement_system,
        week_start=request.week_start,
        tracked_domains=request.tracked_domains,
    )


def profile_response(profile: WellnessProfile) -> WellnessProfileResponse:
    return WellnessProfileResponse(
        profile_id=UUID(profile.profile_id.value),
        time_zone=profile.time_zone,
        display_name=profile.display_name,
        measurement_system=profile.measurement_system,
        week_start=profile.week_start,
        tracked_domains=profile.tracked_domains,
    )


def goal_from_request(
    request: WellnessGoalRequest,
    *,
    goal_id: GoalId,
    profile_id: ProfileId,
) -> WellnessGoal:
    return WellnessGoal(
        goal_id=goal_id,
        profile_id=profile_id,
        target=GoalTarget(
            metric=request.target.metric,
            value=request.target.value,
            unit=request.target.unit,
        ),
        direction=request.direction,
        status=request.status,
        start_date=request.start_date,
        target_date=request.target_date,
        title=request.title,
        description=request.description,
    )


def goal_response(goal: WellnessGoal) -> WellnessGoalResponse:
    return WellnessGoalResponse(
        goal_id=UUID(goal.goal_id.value),
        target=GoalTargetData(
            metric=goal.target.metric,
            value=goal.target.value,
            unit=goal.target.unit,
        ),
        direction=goal.direction,
        status=goal.status,
        start_date=goal.start_date,
        target_date=goal.target_date,
        title=goal.title,
        description=goal.description,
    )


def _metadata(request: RecordMetadataRequest) -> RecordMetadata:
    return RecordMetadata(RecordId.generate(), request.recorded_at, request.source, request.notes)


def _nutrition(data: MealNutritionData) -> MealNutrition:
    return MealNutrition(**data.model_dump())


def record_from_request(request: WellnessRecordCreateRequest) -> WellnessRecord:
    metadata = _metadata(request.metadata)
    data = request.data
    if isinstance(request, SleepRecordRequest):
        return SleepRecord(
            metadata,
            TimeRange(data.period.start, data.period.end),
            data.sleep_minutes,
            data.awake_minutes,
            data.quality,
            None if data.stages is None else SleepStageDurations(**data.stages.model_dump()),
            data.interruption_count,
        )
    if isinstance(request, DailyActivityRecordRequest):
        return DailyActivityRecord(metadata, **data.model_dump())
    if isinstance(request, WorkoutRecordRequest):
        return WorkoutRecord(
            metadata,
            TimeRange(data.period.start, data.period.end),
            data.workout_type,
            data.distance_kilometers,
            data.active_calories_kcal,
            None if data.perceived_exertion is None else PerceivedExertion(data.perceived_exertion),
            data.average_heart_rate_bpm,
        )
    if isinstance(request, HydrationRecordRequest):
        return HydrationRecord(metadata, **data.model_dump())
    if isinstance(request, MealRecordRequest):
        return MealRecord(metadata, data.meal_type, _nutrition(data.nutrition), data.name)
    if isinstance(request, DailyNutritionRecordRequest):
        return DailyNutritionRecord(
            metadata,
            data.nutrition_date,
            _nutrition(data.nutrition),
            data.meal_count,
        )
    if isinstance(request, BodyMeasurementRecordRequest):
        return BodyMeasurementRecord(metadata, **data.model_dump())
    if isinstance(request, SubjectiveCheckInRecordRequest):
        return SubjectiveWellnessCheckIn(
            metadata,
            SubjectiveScore(data.mood_score),
            SubjectiveScore(data.energy_score),
            SubjectiveScore(data.stress_score),
            None if data.motivation_score is None else SubjectiveScore(data.motivation_score),
            data.mood_category,
            data.tags,
        )
    if isinstance(request, MenstrualBleedingRecordRequest):
        return MenstrualBleedingRecord(
            metadata,
            data.flow,
            tuple(CycleSymptomEntry(item.symptom, item.intensity) for item in data.symptoms),
        )
    if isinstance(request, MenstrualCycleRecordRequest):
        return MenstrualCycleRecord(metadata, data.start_date, data.end_date)
    raise TypeError("unsupported wellness record request")


def _metadata_response(metadata: RecordMetadata) -> RecordMetadataResponse:
    return RecordMetadataResponse(
        record_id=metadata.record_id.value,
        recorded_at=metadata.recorded_at,
        source=metadata.source,
        notes=metadata.notes,
    )


def _nutrition_data(nutrition: MealNutrition) -> MealNutritionData:
    return MealNutritionData(
        calories_kcal=nutrition.calories_kcal,
        protein_grams=nutrition.protein_grams,
        carbohydrates_grams=nutrition.carbohydrates_grams,
        fat_grams=nutrition.fat_grams,
        fibre_grams=nutrition.fibre_grams,
    )


def record_response(record: WellnessRecord) -> WellnessRecordResponse:
    metadata = _metadata_response(record.metadata)
    if isinstance(record, SleepRecord):
        stages = record.stages
        data = SleepData(
            period=TimeRangeData(start=record.period.start, end=record.period.end),
            sleep_minutes=record.sleep_minutes,
            awake_minutes=record.awake_minutes,
            quality=record.quality,
            stages=None
            if stages is None
            else SleepStageData(
                **{
                    name: getattr(stages, name)
                    for name in ("awake_minutes", "light_minutes", "deep_minutes", "rem_minutes")
                }
            ),
            interruption_count=record.interruption_count,
        )
        kind = "sleep"
    elif isinstance(record, DailyActivityRecord):
        data = DailyActivityData(
            activity_date=record.activity_date,
            steps=record.steps,
            distance_kilometers=record.distance_kilometers,
            active_minutes=record.active_minutes,
            active_calories_kcal=record.active_calories_kcal,
        )
        kind = "daily_activity"
    elif isinstance(record, WorkoutRecord):
        data = WorkoutData(
            period=TimeRangeData(start=record.period.start, end=record.period.end),
            workout_type=record.workout_type,
            distance_kilometers=record.distance_kilometers,
            active_calories_kcal=record.active_calories_kcal,
            perceived_exertion=None
            if record.perceived_exertion is None
            else record.perceived_exertion.score,
            average_heart_rate_bpm=record.average_heart_rate_bpm,
        )
        kind = "workout"
    elif isinstance(record, HydrationRecord):
        data = HydrationData(
            volume_milliliters=record.volume_milliliters,
            beverage_type=record.beverage_type,
            caffeine_milligrams=record.caffeine_milligrams,
        )
        kind = "hydration"
    elif isinstance(record, MealRecord):
        data = MealData(
            meal_type=record.meal_type,
            nutrition=_nutrition_data(record.nutrition),
            name=record.name,
        )
        kind = "meal"
    elif isinstance(record, DailyNutritionRecord):
        data = DailyNutritionData(
            nutrition_date=record.nutrition_date,
            nutrition=_nutrition_data(record.nutrition),
            meal_count=record.meal_count,
        )
        kind = "daily_nutrition"
    elif isinstance(record, BodyMeasurementRecord):
        data = BodyMeasurementData(
            weight_kilograms=record.weight_kilograms,
            height_meters=record.height_meters,
            body_fat_percent=record.body_fat_percent,
            waist_circumference_centimeters=record.waist_circumference_centimeters,
        )
        kind = "body_measurement"
    elif isinstance(record, SubjectiveWellnessCheckIn):
        data = SubjectiveCheckInData(
            mood_score=record.mood_score.value,
            energy_score=record.energy_score.value,
            stress_score=record.stress_score.value,
            motivation_score=None
            if record.motivation_score is None
            else record.motivation_score.value,
            mood_category=record.mood_category,
            tags=record.tags,
        )
        kind = "subjective_check_in"
    elif isinstance(record, MenstrualBleedingRecord):
        data = MenstrualBleedingData(
            flow=record.flow,
            symptoms=tuple(
                CycleSymptomData(symptom=item.symptom, intensity=item.intensity)
                for item in record.symptoms
            ),
        )
        kind = "menstrual_bleeding"
    elif isinstance(record, MenstrualCycleRecord):
        data = MenstrualCycleData(start_date=record.start_date, end_date=record.end_date)
        kind = "menstrual_cycle"
    else:
        raise TypeError("unsupported wellness record")
    return WellnessRecordResponse(record_type=kind, metadata=metadata, data=data)


def _time_range_data(time_range: TimeRange | None) -> TimeRangeData | None:
    if time_range is None:
        return None
    return TimeRangeData(start=time_range.start, end=time_range.end)


def summary_response(summary: WellnessSummary) -> WellnessSummaryResponse:
    metric_responses = []
    for metric_summary in summary.metrics:
        baseline = metric_summary.baseline
        trend = metric_summary.trend
        metric_responses.append(
            MetricWellnessSummaryResponse(
                metric=metric_summary.metric,
                unit=metric_summary.unit,
                baseline=PersonalBaselineResponse(
                    sample_count=baseline.sample_count,
                    mean=baseline.mean,
                    median=baseline.median,
                    minimum=baseline.minimum,
                    maximum=baseline.maximum,
                    population_standard_deviation=baseline.population_standard_deviation,
                    first_observed_at=baseline.first_observed_at,
                    last_observed_at=baseline.last_observed_at,
                    time_range=_time_range_data(baseline.time_range),
                ),
                trend=None
                if trend is None
                else WellnessTrendResponse(
                    sample_count=trend.sample_count,
                    first_value=trend.first_value,
                    last_value=trend.last_value,
                    absolute_change=trend.absolute_change,
                    percentage_change=trend.percentage_change,
                    slope_per_day=trend.slope_per_day,
                    direction=trend.direction,
                    stability_tolerance=trend.stability_tolerance,
                    first_observed_at=trend.first_observed_at,
                    last_observed_at=trend.last_observed_at,
                    time_range=_time_range_data(trend.time_range),
                ),
            )
        )
    return WellnessSummaryResponse(
        metrics=tuple(metric_responses),
        time_range=_time_range_data(summary.time_range),
        generated_from_record_count=summary.generated_from_record_count,
    )
