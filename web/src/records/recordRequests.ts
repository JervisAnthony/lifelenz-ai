import type {
  BeverageType,
  CheckInTag,
  HydrationRecordCreateRequest,
  MoodCategory,
  SleepQuality,
  SleepRecordCreateRequest,
  SubjectiveCheckInCreateRequest,
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
