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
