import type {
  WellnessRecord,
  WellnessRecordCreateRequest,
} from '../api/types';
import { awareIsoToLocalDateTime } from './dateTime';
import type {
  BodyMeasurementFormValue,
  CheckInFormValue,
  DailyActivityFormValue,
  DailyNutritionFormValue,
  HydrationFormValue,
  MealFormValue,
  MenstrualBleedingFormValue,
  MenstrualCycleFormValue,
  NutritionFormValue,
  SleepFormValue,
  WorkoutFormValue,
} from './recordRequests';

function numericText(value: number | null | undefined): string {
  return value === null || value === undefined ? '' : String(value);
}

function notes(record: WellnessRecord): string {
  return record.metadata.notes ?? '';
}

function nutritionValue(data: {
  calories_kcal: number | null;
  protein_grams: number | null;
  carbohydrates_grams: number | null;
  fat_grams: number | null;
  fibre_grams: number | null;
}): NutritionFormValue {
  return {
    caloriesKcal: numericText(data.calories_kcal),
    proteinGrams: numericText(data.protein_grams),
    carbohydratesGrams: numericText(data.carbohydrates_grams),
    fatGrams: numericText(data.fat_grams),
    fibreGrams: numericText(data.fibre_grams),
  };
}

export function sleepEditValue(record?: WellnessRecord): SleepFormValue | null {
  if (record?.record_type !== 'sleep') return null;
  return {
    start: awareIsoToLocalDateTime(record.data.period.start),
    end: awareIsoToLocalDateTime(record.data.period.end),
    sleepMinutes: String(record.data.sleep_minutes),
    awakeMinutes: String(record.data.awake_minutes),
    quality: record.data.quality ?? '',
    interruptionCount: numericText(record.data.interruption_count),
    notes: notes(record),
  };
}

export function hydrationEditValue(
  record?: WellnessRecord,
): HydrationFormValue | null {
  if (record?.record_type !== 'hydration') return null;
  return {
    recordedAt: awareIsoToLocalDateTime(record.metadata.recorded_at),
    volume: String(record.data.volume_milliliters),
    beverageType: record.data.beverage_type,
    caffeine: numericText(record.data.caffeine_milligrams),
    notes: notes(record),
  };
}

export function checkInEditValue(record?: WellnessRecord): CheckInFormValue | null {
  if (record?.record_type !== 'subjective_check_in') return null;
  return {
    recordedAt: awareIsoToLocalDateTime(record.metadata.recorded_at),
    mood: String(record.data.mood_score),
    energy: String(record.data.energy_score),
    stress: String(record.data.stress_score),
    motivation: numericText(record.data.motivation_score),
    moodCategory: record.data.mood_category ?? '',
    tags: [...record.data.tags],
    notes: notes(record),
  };
}

export function dailyActivityEditValue(
  record?: WellnessRecord,
): DailyActivityFormValue | null {
  if (record?.record_type !== 'daily_activity') return null;
  return {
    recordedAt: awareIsoToLocalDateTime(record.metadata.recorded_at),
    activityDate: record.data.activity_date,
    steps: String(record.data.steps),
    distanceKilometers: String(record.data.distance_kilometers),
    activeMinutes: String(record.data.active_minutes),
    activeCaloriesKcal: String(record.data.active_calories_kcal),
    notes: notes(record),
  };
}

export function workoutEditValue(record?: WellnessRecord): WorkoutFormValue | null {
  if (record?.record_type !== 'workout') return null;
  return {
    start: awareIsoToLocalDateTime(record.data.period.start),
    end: awareIsoToLocalDateTime(record.data.period.end),
    workoutType: record.data.workout_type,
    distanceKilometers: numericText(record.data.distance_kilometers),
    activeCaloriesKcal: numericText(record.data.active_calories_kcal),
    perceivedExertion: numericText(record.data.perceived_exertion),
    averageHeartRateBpm: numericText(record.data.average_heart_rate_bpm),
    notes: notes(record),
  };
}

export function bodyMeasurementEditValue(
  record?: WellnessRecord,
): BodyMeasurementFormValue | null {
  if (record?.record_type !== 'body_measurement') return null;
  return {
    recordedAt: awareIsoToLocalDateTime(record.metadata.recorded_at),
    weightKilograms: String(record.data.weight_kilograms),
    heightMeters: numericText(record.data.height_meters),
    bodyFatPercent: numericText(record.data.body_fat_percent),
    waistCircumferenceCentimeters: numericText(
      record.data.waist_circumference_centimeters,
    ),
    notes: notes(record),
  };
}

export function mealEditValue(record?: WellnessRecord): MealFormValue | null {
  if (record?.record_type !== 'meal') return null;
  return {
    recordedAt: awareIsoToLocalDateTime(record.metadata.recorded_at),
    mealType: record.data.meal_type,
    name: record.data.name ?? '',
    nutrition: nutritionValue(record.data.nutrition),
    notes: notes(record),
  };
}

export function dailyNutritionEditValue(
  record?: WellnessRecord,
): DailyNutritionFormValue | null {
  if (record?.record_type !== 'daily_nutrition') return null;
  return {
    recordedAt: awareIsoToLocalDateTime(record.metadata.recorded_at),
    nutritionDate: record.data.nutrition_date,
    mealCount: numericText(record.data.meal_count),
    nutrition: nutritionValue(record.data.nutrition),
    notes: notes(record),
  };
}

export function menstrualBleedingEditValue(
  record?: WellnessRecord,
): MenstrualBleedingFormValue | null {
  if (record?.record_type !== 'menstrual_bleeding') return null;
  return {
    recordedAt: awareIsoToLocalDateTime(record.metadata.recorded_at),
    flow: record.data.flow,
    symptoms: record.data.symptoms.map((entry) => ({
      symptom: entry.symptom,
      intensity: entry.intensity ?? '',
    })),
    notes: notes(record),
  };
}

export function menstrualCycleEditValue(
  record?: WellnessRecord,
): MenstrualCycleFormValue | null {
  if (record?.record_type !== 'menstrual_cycle') return null;
  return {
    recordedAt: awareIsoToLocalDateTime(record.metadata.recorded_at),
    startDate: record.data.start_date,
    endDate: record.data.end_date ?? '',
    notes: notes(record),
  };
}

export function prepareCorrectionRequest(
  original: WellnessRecord,
  request: WellnessRecordCreateRequest,
): WellnessRecordCreateRequest {
  if (original.record_type !== request.record_type) {
    throw new Error('A wellness record cannot change type during correction.');
  }

  const metadata = {
    ...request.metadata,
    source: original.metadata.source,
    recorded_at:
      original.record_type === 'sleep' || original.record_type === 'workout'
        ? original.metadata.recorded_at
        : request.metadata.recorded_at,
  };

  if (original.record_type === 'sleep' && request.record_type === 'sleep') {
    return {
      ...request,
      metadata,
      data: {
        ...request.data,
        stages: original.data.stages,
      },
    };
  }

  return { ...request, metadata } as WellnessRecordCreateRequest;
}
