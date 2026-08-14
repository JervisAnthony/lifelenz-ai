import type {
  GoalDirection,
  GoalStatus,
  MeasurementUnit,
  MetricIdentifier,
} from '../api/types';

export const metricOptions: ReadonlyArray<{
  value: MetricIdentifier;
  label: string;
  unit: MeasurementUnit;
}> = [
  { value: 'sleep_duration', label: 'Sleep duration', unit: 'hours' },
  { value: 'time_in_bed', label: 'Time in bed', unit: 'hours' },
  { value: 'sleep_efficiency', label: 'Sleep efficiency', unit: 'percent' },
  { value: 'steps', label: 'Steps', unit: 'count' },
  { value: 'distance', label: 'Distance', unit: 'kilometers' },
  { value: 'active_minutes', label: 'Active minutes', unit: 'minutes' },
  { value: 'active_calories', label: 'Active energy', unit: 'kcal' },
  { value: 'water_intake', label: 'Water intake', unit: 'milliliters' },
  { value: 'calories', label: 'Nutrition energy', unit: 'kcal' },
  { value: 'protein', label: 'Protein', unit: 'grams' },
  { value: 'carbohydrates', label: 'Carbohydrates', unit: 'grams' },
  { value: 'fat', label: 'Fat', unit: 'grams' },
  { value: 'fibre', label: 'Fibre', unit: 'grams' },
  { value: 'weight', label: 'Weight', unit: 'kilograms' },
  { value: 'height', label: 'Height', unit: 'meters' },
  {
    value: 'bmi',
    label: 'Body mass index',
    unit: 'kilograms_per_square_meter',
  },
  { value: 'body_fat', label: 'Body fat', unit: 'percent' },
  { value: 'mood_score', label: 'Mood score', unit: 'score' },
  { value: 'energy_score', label: 'Energy score', unit: 'score' },
  { value: 'stress_score', label: 'Stress score', unit: 'score' },
  { value: 'recovery_score', label: 'Recovery score', unit: 'score' },
];

export const directionOptions: ReadonlyArray<{
  value: GoalDirection;
  label: string;
}> = [
  { value: 'at_least', label: 'At least' },
  { value: 'at_most', label: 'At most' },
  { value: 'exactly', label: 'Exactly' },
  { value: 'increase', label: 'Increase' },
  { value: 'decrease', label: 'Decrease' },
  { value: 'maintain', label: 'Maintain' },
];

export const statusOptions: ReadonlyArray<{
  value: GoalStatus;
  label: string;
}> = [
  { value: 'draft', label: 'Draft' },
  { value: 'active', label: 'Active' },
  { value: 'paused', label: 'Paused' },
  { value: 'completed', label: 'Completed' },
  { value: 'cancelled', label: 'Cancelled' },
];

export const unitLabels: Record<MeasurementUnit, string> = {
  minutes: 'minutes',
  hours: 'hours',
  meters: 'meters',
  kilometers: 'kilometers',
  grams: 'grams',
  kilograms: 'kilograms',
  kilograms_per_square_meter: 'kg/m²',
  milliliters: 'milliliters',
  liters: 'liters',
  kcal: 'kcal',
  percent: 'percent',
  count: 'count',
  score: 'score',
};

const metricDefinitions = Object.fromEntries(
  metricOptions.map((option) => [option.value, option]),
) as Record<MetricIdentifier, (typeof metricOptions)[number]>;
const directionLabels = Object.fromEntries(
  directionOptions.map((option) => [option.value, option.label]),
) as Record<GoalDirection, string>;
const statusLabels = Object.fromEntries(
  statusOptions.map((option) => [option.value, option.label]),
) as Record<GoalStatus, string>;

export function metricDefinition(metric: MetricIdentifier) {
  return metricDefinitions[metric];
}

export function directionLabel(direction: GoalDirection) {
  return directionLabels[direction];
}

export function statusLabel(status: GoalStatus) {
  return statusLabels[status];
}
