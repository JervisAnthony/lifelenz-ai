export interface ApiErrorDetail {
  code: string;
  message: string;
  field: string | null;
}

export interface ApiErrorEnvelope {
  error: ApiErrorDetail;
  request_id: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
}

export interface UserAccount {
  user_id: string;
  email: string;
  is_active: boolean;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface AccessToken {
  access_token: string;
  token_type: 'bearer';
  expires_in: number;
}

export interface CurrentUser extends UserAccount {
  profile_ids: string[];
}

export type MeasurementSystem = 'metric' | 'imperial';
export type WeekStart = 'monday' | 'sunday';
export type TrackedWellnessDomain =
  | 'sleep'
  | 'activity'
  | 'hydration'
  | 'nutrition'
  | 'body_measurements'
  | 'subjective_check_ins'
  | 'menstrual_cycle';

export interface WellnessProfileRequest {
  time_zone: string;
  display_name: string | null;
  measurement_system: MeasurementSystem;
  week_start: WeekStart;
  tracked_domains: TrackedWellnessDomain[];
}

export interface WellnessProfile extends WellnessProfileRequest {
  profile_id: string;
}

export type MetricIdentifier =
  | 'sleep_duration'
  | 'time_in_bed'
  | 'sleep_efficiency'
  | 'steps'
  | 'distance'
  | 'active_minutes'
  | 'active_calories'
  | 'water_intake'
  | 'calories'
  | 'protein'
  | 'carbohydrates'
  | 'fat'
  | 'fibre'
  | 'weight'
  | 'height'
  | 'bmi'
  | 'body_fat'
  | 'mood_score'
  | 'energy_score'
  | 'stress_score'
  | 'recovery_score';

export type MeasurementUnit =
  | 'minutes'
  | 'hours'
  | 'meters'
  | 'kilometers'
  | 'grams'
  | 'kilograms'
  | 'kilograms_per_square_meter'
  | 'milliliters'
  | 'liters'
  | 'kcal'
  | 'percent'
  | 'count'
  | 'score';

export interface TimeRange {
  start: string;
  end: string;
}

export interface PersonalBaseline {
  sample_count: number;
  mean: number;
  median: number;
  minimum: number;
  maximum: number;
  population_standard_deviation: number;
  first_observed_at: string;
  last_observed_at: string;
  time_range: TimeRange | null;
}

export type TrendDirection = 'increasing' | 'decreasing' | 'stable';

export interface WellnessTrend {
  sample_count: number;
  first_value: number;
  last_value: number;
  absolute_change: number;
  percentage_change: number | null;
  slope_per_day: number;
  direction: TrendDirection;
  stability_tolerance: number;
  first_observed_at: string;
  last_observed_at: string;
  time_range: TimeRange | null;
}

export interface MetricWellnessSummary {
  metric: MetricIdentifier;
  unit: MeasurementUnit;
  baseline: PersonalBaseline;
  trend: WellnessTrend | null;
}

export interface WellnessSummary {
  metrics: MetricWellnessSummary[];
  time_range: TimeRange | null;
  generated_from_record_count: number;
}
