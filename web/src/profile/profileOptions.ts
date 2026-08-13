import type {
  MeasurementSystem,
  TrackedWellnessDomain,
  WeekStart,
} from '../api/types';

export const measurementSystemOptions: ReadonlyArray<{
  value: MeasurementSystem;
  label: string;
  description: string;
}> = [
  {
    value: 'metric',
    label: 'Metric',
    description: 'Kilograms, kilometers, and liters',
  },
  {
    value: 'imperial',
    label: 'Imperial',
    description: 'Pounds, miles, and fluid ounces',
  },
];

export const weekStartOptions: ReadonlyArray<{
  value: WeekStart;
  label: string;
}> = [
  { value: 'monday', label: 'Monday' },
  { value: 'sunday', label: 'Sunday' },
];

export const trackedDomainOptions: ReadonlyArray<{
  value: TrackedWellnessDomain;
  label: string;
  description: string;
}> = [
  {
    value: 'sleep',
    label: 'Sleep',
    description: 'Sleep timing, duration, and quality',
  },
  {
    value: 'activity',
    label: 'Activity',
    description: 'Daily movement and workouts',
  },
  {
    value: 'hydration',
    label: 'Hydration',
    description: 'Water and beverage intake',
  },
  {
    value: 'nutrition',
    label: 'Nutrition',
    description: 'Meals and daily nutrition',
  },
  {
    value: 'body_measurements',
    label: 'Body measurements',
    description: 'Neutral measurements recorded over time',
  },
  {
    value: 'subjective_check_ins',
    label: 'Daily check-ins',
    description: 'Mood, energy, stress, and motivation',
  },
  {
    value: 'menstrual_cycle',
    label: 'Menstrual cycle',
    description: 'User-supplied cycle and bleeding observations',
  },
];

export function domainLabel(value: TrackedWellnessDomain): string {
  return (
    trackedDomainOptions.find((option) => option.value === value)?.label ??
    value
  );
}
