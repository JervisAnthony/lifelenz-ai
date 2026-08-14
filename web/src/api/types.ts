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

export type WellnessRecordType =
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

export type DataSource = 'manual' | 'csv_import' | 'app_import' | 'api_import';

export interface RecordMetadataRequest {
  recorded_at: string;
  source: DataSource;
  notes: string | null;
}

export interface RecordMetadata extends RecordMetadataRequest {
  record_id: string;
}

export type SleepQuality = 'very_poor' | 'poor' | 'fair' | 'good' | 'very_good';

export interface SleepStageData {
  awake_minutes: number;
  light_minutes: number;
  deep_minutes: number;
  rem_minutes: number;
}

export interface SleepData {
  period: TimeRange;
  sleep_minutes: number;
  awake_minutes: number;
  quality: SleepQuality | null;
  stages: SleepStageData | null;
  interruption_count: number | null;
}

export interface DailyActivityData {
  activity_date: string;
  steps: number;
  distance_kilometers: number;
  active_minutes: number;
  active_calories_kcal: number;
}

export type WorkoutType =
  | 'walking'
  | 'running'
  | 'cycling'
  | 'swimming'
  | 'strength_training'
  | 'yoga'
  | 'hiking'
  | 'rowing'
  | 'elliptical'
  | 'sport'
  | 'other';

export interface WorkoutData {
  period: TimeRange;
  workout_type: WorkoutType;
  distance_kilometers: number | null;
  active_calories_kcal: number | null;
  perceived_exertion: number | null;
  average_heart_rate_bpm: number | null;
}

export type BeverageType =
  | 'water'
  | 'sparkling_water'
  | 'tea'
  | 'coffee'
  | 'juice'
  | 'milk'
  | 'sports_drink'
  | 'other';

export interface HydrationData {
  volume_milliliters: number;
  beverage_type: BeverageType;
  caffeine_milligrams: number | null;
}

export type MealType = 'breakfast' | 'lunch' | 'dinner' | 'snack' | 'other';

export interface MealNutritionData {
  calories_kcal: number | null;
  protein_grams: number | null;
  carbohydrates_grams: number | null;
  fat_grams: number | null;
  fibre_grams: number | null;
}

export interface MealData {
  meal_type: MealType;
  nutrition: MealNutritionData;
  name: string | null;
}

export interface DailyNutritionData {
  nutrition_date: string;
  nutrition: MealNutritionData;
  meal_count: number | null;
}

export interface BodyMeasurementData {
  weight_kilograms: number;
  height_meters: number | null;
  body_fat_percent: number | null;
  waist_circumference_centimeters: number | null;
}

export type MoodCategory =
  'very_low' | 'low' | 'neutral' | 'high' | 'very_high';

export type CheckInTag =
  | 'rested'
  | 'tired'
  | 'focused'
  | 'distracted'
  | 'calm'
  | 'tense'
  | 'motivated'
  | 'unmotivated'
  | 'social'
  | 'solitary'
  | 'other';

export interface SubjectiveCheckInData {
  mood_score: number;
  energy_score: number;
  stress_score: number;
  motivation_score: number | null;
  mood_category: MoodCategory | null;
  tags: CheckInTag[];
}

export type MenstrualFlow = 'spotting' | 'light' | 'moderate' | 'heavy';
export type CycleSymptom =
  | 'cramps'
  | 'bloating'
  | 'headache'
  | 'back_discomfort'
  | 'breast_tenderness'
  | 'fatigue'
  | 'mood_change'
  | 'nausea'
  | 'acne'
  | 'food_craving'
  | 'sleep_change'
  | 'other';
export type SymptomIntensity = 'mild' | 'moderate' | 'strong';

export interface MenstrualBleedingData {
  flow: MenstrualFlow;
  symptoms: Array<{
    symptom: CycleSymptom;
    intensity: SymptomIntensity | null;
  }>;
}

export interface MenstrualCycleData {
  start_date: string;
  end_date: string | null;
}

type WellnessRecordFor<TType extends WellnessRecordType, TData> = {
  record_type: TType;
  metadata: RecordMetadata;
  data: TData;
};

export type WellnessRecord =
  | WellnessRecordFor<'sleep', SleepData>
  | WellnessRecordFor<'daily_activity', DailyActivityData>
  | WellnessRecordFor<'workout', WorkoutData>
  | WellnessRecordFor<'hydration', HydrationData>
  | WellnessRecordFor<'meal', MealData>
  | WellnessRecordFor<'daily_nutrition', DailyNutritionData>
  | WellnessRecordFor<'body_measurement', BodyMeasurementData>
  | WellnessRecordFor<'subjective_check_in', SubjectiveCheckInData>
  | WellnessRecordFor<'menstrual_bleeding', MenstrualBleedingData>
  | WellnessRecordFor<'menstrual_cycle', MenstrualCycleData>;

export interface SleepRecordCreateRequest {
  record_type: 'sleep';
  metadata: RecordMetadataRequest;
  data: SleepData;
}

export interface HydrationRecordCreateRequest {
  record_type: 'hydration';
  metadata: RecordMetadataRequest;
  data: HydrationData;
}

export interface SubjectiveCheckInCreateRequest {
  record_type: 'subjective_check_in';
  metadata: RecordMetadataRequest;
  data: SubjectiveCheckInData;
}

export interface DailyActivityRecordCreateRequest {
  record_type: 'daily_activity';
  metadata: RecordMetadataRequest;
  data: {
    activity_date: string;
    steps?: number;
    distance_kilometers?: number;
    active_minutes?: number;
    active_calories_kcal?: number;
  };
}

export interface WorkoutRecordCreateRequest {
  record_type: 'workout';
  metadata: RecordMetadataRequest;
  data: WorkoutData;
}

export interface BodyMeasurementRecordCreateRequest {
  record_type: 'body_measurement';
  metadata: RecordMetadataRequest;
  data: BodyMeasurementData;
}

export type WellnessRecordCreateRequest =
  | SleepRecordCreateRequest
  | HydrationRecordCreateRequest
  | SubjectiveCheckInCreateRequest
  | DailyActivityRecordCreateRequest
  | WorkoutRecordCreateRequest
  | BodyMeasurementRecordCreateRequest;
