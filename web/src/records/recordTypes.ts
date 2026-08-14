import type { WellnessRecordType } from '../api/types';

export const recordTypeLabels: Record<WellnessRecordType, string> = {
  sleep: 'Sleep',
  daily_activity: 'Daily activity',
  workout: 'Workout',
  hydration: 'Hydration',
  meal: 'Meal',
  daily_nutrition: 'Daily nutrition',
  body_measurement: 'Body measurement',
  subjective_check_in: 'Wellness check-in',
  menstrual_bleeding: 'Menstrual bleeding observation',
  menstrual_cycle: 'Menstrual cycle',
};

export type RecordEntryType =
  | 'sleep'
  | 'daily_activity'
  | 'workout'
  | 'hydration'
  | 'meal'
  | 'daily_nutrition'
  | 'body_measurement'
  | 'subjective_check_in'
  | 'menstrual_bleeding'
  | 'menstrual_cycle';

export const recordEntryOptions: ReadonlyArray<{
  type: RecordEntryType;
  label: string;
  description: string;
}> = [
  {
    type: 'sleep',
    label: 'Sleep',
    description: 'Record a completed sleep session and its timing.',
  },
  {
    type: 'daily_activity',
    label: 'Daily activity',
    description: 'Record movement totals for a calendar date.',
  },
  {
    type: 'workout',
    label: 'Workout',
    description: 'Record a completed workout and its timing.',
  },
  {
    type: 'hydration',
    label: 'Hydration',
    description: 'Record a beverage and its canonical milliliter volume.',
  },
  {
    type: 'meal',
    label: 'Meal',
    description: 'Record one meal event with known nutrition measurements.',
  },
  {
    type: 'daily_nutrition',
    label: 'Daily nutrition',
    description: 'Record nutrition totals for one calendar date.',
  },
  {
    type: 'body_measurement',
    label: 'Body measurement',
    description: 'Record neutral measurements in canonical units.',
  },
  {
    type: 'subjective_check_in',
    label: 'Wellness check-in',
    description: 'Record your own mood, energy, and stress scores.',
  },
  {
    type: 'menstrual_bleeding',
    label: 'Menstrual bleeding observation',
    description: 'Record a user-reported bleeding observation.',
  },
  {
    type: 'menstrual_cycle',
    label: 'Menstrual cycle',
    description: 'Record a user-supplied cycle date range.',
  },
];
