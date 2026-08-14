import type {
  BeverageType,
  BodyMeasurementRecordCreateRequest,
  CheckInTag,
  DailyActivityRecordCreateRequest,
  HydrationRecordCreateRequest,
  MoodCategory,
  SleepQuality,
  SleepRecordCreateRequest,
  SubjectiveCheckInCreateRequest,
  WorkoutRecordCreateRequest,
  WorkoutType,
} from '../api/types';
import { elapsedMinutes, localDateTimeToAwareIso } from './dateTime';
import { metadata } from './forms/formTypes';

export interface SleepFormValue {
  start: string;
  end: string;
  sleepMinutes: string;
  awakeMinutes: string;
  quality: SleepQuality | '';
  interruptionCount: string;
  notes: string;
}

export function buildSleepRecordRequest(
  value: SleepFormValue,
): SleepRecordCreateRequest {
  const periodMinutes = elapsedMinutes(value.start, value.end);
  const sleepMinutes = Number(value.sleepMinutes);
  const awakeMinutes = Number(value.awakeMinutes);
  if (periodMinutes <= 0) {
    throw new Error('Sleep end must be after sleep start.');
  }
  if (!Number.isFinite(sleepMinutes) || sleepMinutes <= 0) {
    throw new Error('Enter sleep minutes greater than zero.');
  }
  if (!Number.isFinite(awakeMinutes) || awakeMinutes < 0) {
    throw new Error('Awake minutes cannot be negative.');
  }
  if (sleepMinutes + awakeMinutes > periodMinutes) {
    throw new Error(
      'Sleep and awake minutes cannot exceed the time between start and end.',
    );
  }
  let interruptionCount: number | null = null;
  if (value.interruptionCount !== '') {
    interruptionCount = Number(value.interruptionCount);
    if (!Number.isInteger(interruptionCount) || interruptionCount < 0) {
      throw new Error('Interruptions must be a whole number of zero or more.');
    }
  }
  const end = localDateTimeToAwareIso(value.end);
  return {
    record_type: 'sleep',
    metadata: metadata(end, value.notes),
    data: {
      period: {
        start: localDateTimeToAwareIso(value.start),
        end,
      },
      sleep_minutes: sleepMinutes,
      awake_minutes: awakeMinutes,
      quality: value.quality || null,
      stages: null,
      interruption_count: interruptionCount,
    },
  };
}

export interface HydrationFormValue {
  recordedAt: string;
  volume: string;
  beverageType: BeverageType;
  caffeine: string;
  notes: string;
}

export function buildHydrationRecordRequest(
  value: HydrationFormValue,
): HydrationRecordCreateRequest {
  const volume = Number(value.volume);
  if (!Number.isFinite(volume) || volume <= 0) {
    throw new Error('Enter a volume greater than zero milliliters.');
  }
  let caffeine: number | null = null;
  if (value.caffeine !== '') {
    caffeine = Number(value.caffeine);
    if (!Number.isFinite(caffeine) || caffeine < 0) {
      throw new Error('Caffeine cannot be negative.');
    }
  }
  return {
    record_type: 'hydration',
    metadata: metadata(localDateTimeToAwareIso(value.recordedAt), value.notes),
    data: {
      volume_milliliters: volume,
      beverage_type: value.beverageType,
      caffeine_milligrams: caffeine,
    },
  };
}

export interface CheckInFormValue {
  recordedAt: string;
  mood: string;
  energy: string;
  stress: string;
  motivation: string;
  moodCategory: MoodCategory | '';
  tags: CheckInTag[];
  notes: string;
}

function requiredScore(value: string, label: string): number {
  const score = Number(value);
  if (!Number.isInteger(score) || score < 1 || score > 10) {
    throw new Error(`Choose a ${label.toLowerCase()} score from 1 through 10.`);
  }
  return score;
}

export function buildSubjectiveCheckInRequest(
  value: CheckInFormValue,
): SubjectiveCheckInCreateRequest {
  const motivation = value.motivation
    ? requiredScore(value.motivation, 'Motivation')
    : null;
  return {
    record_type: 'subjective_check_in',
    metadata: metadata(localDateTimeToAwareIso(value.recordedAt), value.notes),
    data: {
      mood_score: requiredScore(value.mood, 'Mood'),
      energy_score: requiredScore(value.energy, 'Energy'),
      stress_score: requiredScore(value.stress, 'Stress'),
      motivation_score: motivation,
      mood_category: value.moodCategory || null,
      tags: value.tags,
    },
  };
}

function optionalNonNegativeNumber(value: string, label: string) {
  if (value === '') {
    return null;
  }
  const number = Number(value);
  if (!Number.isFinite(number) || number < 0) {
    throw new Error(`${label} cannot be negative.`);
  }
  return number;
}

function optionalPositiveNumber(value: string, label: string) {
  if (value === '') {
    return null;
  }
  const number = Number(value);
  if (!Number.isFinite(number) || number <= 0) {
    throw new Error(`${label} must be greater than zero.`);
  }
  return number;
}

export interface DailyActivityFormValue {
  recordedAt: string;
  activityDate: string;
  steps: string;
  distanceKilometers: string;
  activeMinutes: string;
  activeCaloriesKcal: string;
  notes: string;
}

export function buildDailyActivityRecordRequest(
  value: DailyActivityFormValue,
): DailyActivityRecordCreateRequest {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value.activityDate)) {
    throw new Error('Enter a complete activity date.');
  }
  const steps = value.steps === '' ? null : Number(value.steps);
  if (steps !== null && (!Number.isInteger(steps) || steps < 0)) {
    throw new Error('Steps must be a whole number of zero or more.');
  }
  const distance = optionalNonNegativeNumber(
    value.distanceKilometers,
    'Distance',
  );
  const activeMinutes = optionalNonNegativeNumber(
    value.activeMinutes,
    'Active minutes',
  );
  const activeCalories = optionalNonNegativeNumber(
    value.activeCaloriesKcal,
    'Active calories',
  );
  return {
    record_type: 'daily_activity',
    metadata: metadata(localDateTimeToAwareIso(value.recordedAt), value.notes),
    data: {
      activity_date: value.activityDate,
      ...(steps === null ? {} : { steps }),
      ...(distance === null ? {} : { distance_kilometers: distance }),
      ...(activeMinutes === null ? {} : { active_minutes: activeMinutes }),
      ...(activeCalories === null
        ? {}
        : { active_calories_kcal: activeCalories }),
    },
  };
}

export interface WorkoutFormValue {
  start: string;
  end: string;
  workoutType: WorkoutType;
  distanceKilometers: string;
  activeCaloriesKcal: string;
  perceivedExertion: string;
  averageHeartRateBpm: string;
  notes: string;
}

export function buildWorkoutRecordRequest(
  value: WorkoutFormValue,
): WorkoutRecordCreateRequest {
  if (elapsedMinutes(value.start, value.end) <= 0) {
    throw new Error('Workout end must be after workout start.');
  }
  let perceivedExertion: number | null = null;
  if (value.perceivedExertion !== '') {
    perceivedExertion = Number(value.perceivedExertion);
    if (
      !Number.isInteger(perceivedExertion) ||
      perceivedExertion < 1 ||
      perceivedExertion > 10
    ) {
      throw new Error(
        'Perceived exertion must be a whole number from 1 through 10.',
      );
    }
  }
  const end = localDateTimeToAwareIso(value.end);
  return {
    record_type: 'workout',
    metadata: metadata(end, value.notes),
    data: {
      period: {
        start: localDateTimeToAwareIso(value.start),
        end,
      },
      workout_type: value.workoutType,
      distance_kilometers: optionalNonNegativeNumber(
        value.distanceKilometers,
        'Distance',
      ),
      active_calories_kcal: optionalNonNegativeNumber(
        value.activeCaloriesKcal,
        'Active calories',
      ),
      perceived_exertion: perceivedExertion,
      average_heart_rate_bpm: optionalPositiveNumber(
        value.averageHeartRateBpm,
        'Average heart rate',
      ),
    },
  };
}

export interface BodyMeasurementFormValue {
  recordedAt: string;
  weightKilograms: string;
  heightMeters: string;
  bodyFatPercent: string;
  waistCircumferenceCentimeters: string;
  notes: string;
}

export function buildBodyMeasurementRecordRequest(
  value: BodyMeasurementFormValue,
): BodyMeasurementRecordCreateRequest {
  const weight = Number(value.weightKilograms);
  if (!Number.isFinite(weight) || weight <= 0) {
    throw new Error('Weight must be greater than zero kilograms.');
  }
  const bodyFat = optionalNonNegativeNumber(
    value.bodyFatPercent,
    'Body fat percentage',
  );
  if (bodyFat !== null && bodyFat > 100) {
    throw new Error('Body fat percentage cannot exceed 100.');
  }
  return {
    record_type: 'body_measurement',
    metadata: metadata(localDateTimeToAwareIso(value.recordedAt), value.notes),
    data: {
      weight_kilograms: weight,
      height_meters: optionalPositiveNumber(value.heightMeters, 'Height'),
      body_fat_percent: bodyFat,
      waist_circumference_centimeters: optionalPositiveNumber(
        value.waistCircumferenceCentimeters,
        'Waist circumference',
      ),
    },
  };
}
