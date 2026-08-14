import type {
  WellnessProfile,
  WellnessRecord,
  WellnessSummary,
} from '../api/types';

export const wellnessProfile: WellnessProfile = {
  profile_id: 'c86bd446-d82a-4448-94b0-653b336ccca5',
  time_zone: 'Asia/Kolkata',
  display_name: 'River',
  measurement_system: 'metric',
  week_start: 'monday',
  tracked_domains: ['sleep', 'hydration'],
};

export const wellnessSummary: WellnessSummary = {
  generated_from_record_count: 2,
  time_range: null,
  metrics: [
    {
      metric: 'water_intake',
      unit: 'milliliters',
      baseline: {
        sample_count: 2,
        mean: 375,
        median: 375,
        minimum: 250,
        maximum: 500,
        population_standard_deviation: 125,
        first_observed_at: '2026-01-01T10:00:00+00:00',
        last_observed_at: '2026-01-02T10:00:00+00:00',
        time_range: null,
      },
      trend: {
        sample_count: 2,
        first_value: 250,
        last_value: 500,
        absolute_change: 250,
        percentage_change: 100,
        slope_per_day: 250,
        direction: 'increasing',
        stability_tolerance: 0,
        first_observed_at: '2026-01-01T10:00:00+00:00',
        last_observed_at: '2026-01-02T10:00:00+00:00',
        time_range: null,
      },
    },
  ],
};

export const hydrationRecord: WellnessRecord = {
  record_type: 'hydration',
  metadata: {
    record_id: '5bb91ed2-9d67-4c7e-819b-31df6b4e5cd8',
    recorded_at: '2026-08-14T10:30:00+05:30',
    source: 'manual',
    notes: null,
  },
  data: {
    volume_milliliters: 350,
    beverage_type: 'water',
    caffeine_milligrams: null,
  },
};

export const dailyActivityRecord: WellnessRecord = {
  record_type: 'daily_activity',
  metadata: {
    record_id: '7dd91ed2-9d67-4c7e-819b-31df6b4e5cd8',
    recorded_at: '2026-08-13T10:30:00+05:30',
    source: 'manual',
    notes: null,
  },
  data: {
    activity_date: '2026-08-13',
    steps: 4200,
    distance_kilometers: 3.1,
    active_minutes: 32,
    active_calories_kcal: 180,
  },
};

export const workoutRecord: WellnessRecord = {
  record_type: 'workout',
  metadata: {
    record_id: '8ee91ed2-9d67-4c7e-819b-31df6b4e5cd8',
    recorded_at: '2026-08-14T07:30:00+05:30',
    source: 'manual',
    notes: null,
  },
  data: {
    period: {
      start: '2026-08-14T06:30:00+05:30',
      end: '2026-08-14T07:30:00+05:30',
    },
    workout_type: 'strength_training',
    distance_kilometers: null,
    active_calories_kcal: 240,
    perceived_exertion: 6,
    average_heart_rate_bpm: 118,
  },
};

export const bodyMeasurementRecord: WellnessRecord = {
  record_type: 'body_measurement',
  metadata: {
    record_id: '9ff91ed2-9d67-4c7e-819b-31df6b4e5cd8',
    recorded_at: '2026-08-14T08:00:00+05:30',
    source: 'manual',
    notes: null,
  },
  data: {
    weight_kilograms: 72.4,
    height_meters: 1.78,
    body_fat_percent: null,
    waist_circumference_centimeters: null,
  },
};

export const mealRecord: WellnessRecord = {
  record_type: 'meal',
  metadata: {
    record_id: 'a1a91ed2-9d67-4c7e-819b-31df6b4e5cd8',
    recorded_at: '2026-08-14T12:30:00+05:30',
    source: 'manual',
    notes: null,
  },
  data: {
    meal_type: 'lunch',
    name: 'Rice and vegetables',
    nutrition: {
      calories_kcal: 420,
      protein_grams: null,
      carbohydrates_grams: null,
      fat_grams: null,
      fibre_grams: null,
    },
  },
};

export const dailyNutritionRecord: WellnessRecord = {
  record_type: 'daily_nutrition',
  metadata: {
    record_id: 'b2b91ed2-9d67-4c7e-819b-31df6b4e5cd8',
    recorded_at: '2026-08-14T20:00:00+05:30',
    source: 'manual',
    notes: null,
  },
  data: {
    nutrition_date: '2026-08-14',
    meal_count: null,
    nutrition: {
      calories_kcal: null,
      protein_grams: 24,
      carbohydrates_grams: null,
      fat_grams: null,
      fibre_grams: null,
    },
  },
};

export const menstrualBleedingRecord: WellnessRecord = {
  record_type: 'menstrual_bleeding',
  metadata: {
    record_id: 'c3c91ed2-9d67-4c7e-819b-31df6b4e5cd8',
    recorded_at: '2026-08-14T09:00:00+05:30',
    source: 'manual',
    notes: null,
  },
  data: {
    flow: 'light',
    symptoms: [],
  },
};

export const menstrualCycleRecord: WellnessRecord = {
  record_type: 'menstrual_cycle',
  metadata: {
    record_id: 'd4d91ed2-9d67-4c7e-819b-31df6b4e5cd8',
    recorded_at: '2026-08-14T09:00:00+05:30',
    source: 'manual',
    notes: null,
  },
  data: {
    start_date: '2026-08-14',
    end_date: null,
  },
};
