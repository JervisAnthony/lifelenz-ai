import type { WellnessProfile, WellnessSummary } from '../api/types';

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
