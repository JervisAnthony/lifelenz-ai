import type {
  MeasurementUnit,
  MetricIdentifier,
  TrendDirection,
} from '../api/types';

export const metricLabels: Record<MetricIdentifier, string> = {
  sleep_duration: 'Sleep duration',
  time_in_bed: 'Time in bed',
  sleep_efficiency: 'Sleep efficiency',
  steps: 'Steps',
  distance: 'Distance',
  active_minutes: 'Active minutes',
  active_calories: 'Active calories',
  water_intake: 'Water intake',
  calories: 'Calories',
  protein: 'Protein',
  carbohydrates: 'Carbohydrates',
  fat: 'Fat',
  fibre: 'Fibre',
  weight: 'Weight',
  height: 'Height',
  bmi: 'BMI',
  body_fat: 'Body fat',
  mood_score: 'Mood score',
  energy_score: 'Energy score',
  stress_score: 'Stress score',
  recovery_score: 'Recovery score',
};

const unitLabels: Record<MeasurementUnit, string> = {
  minutes: 'min',
  hours: 'hr',
  meters: 'm',
  kilometers: 'km',
  grams: 'g',
  kilograms: 'kg',
  kilograms_per_square_meter: 'kg/m²',
  milliliters: 'mL',
  liters: 'L',
  kcal: 'kcal',
  percent: '%',
  count: '',
  score: 'score',
};

export const trendLabels: Record<TrendDirection, string> = {
  increasing: 'Increasing',
  decreasing: 'Decreasing',
  stable: 'Stable',
};

export function formatMeasurement(
  value: number,
  unit: MeasurementUnit,
): string {
  const formatted = Number.isInteger(value)
    ? value.toLocaleString()
    : value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  const label = unitLabels[unit];
  return label ? `${formatted} ${label}` : formatted;
}
