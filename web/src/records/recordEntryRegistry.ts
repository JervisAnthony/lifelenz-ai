import type { ComponentType } from 'react';

import { BodyMeasurementRecordForm } from './forms/BodyMeasurementRecordForm';
import { DailyActivityRecordForm } from './forms/DailyActivityRecordForm';
import { DailyNutritionRecordForm } from './forms/DailyNutritionRecordForm';
import { HydrationRecordForm } from './forms/HydrationRecordForm';
import { MealRecordForm } from './forms/MealRecordForm';
import { MenstrualBleedingRecordForm } from './forms/MenstrualBleedingRecordForm';
import { MenstrualCycleRecordForm } from './forms/MenstrualCycleRecordForm';
import { SleepRecordForm } from './forms/SleepRecordForm';
import { SubjectiveCheckInForm } from './forms/SubjectiveCheckInForm';
import { WorkoutRecordForm } from './forms/WorkoutRecordForm';
import type { RecordFormProps } from './forms/formTypes';
import { recordEntryOptions, type RecordEntryType } from './recordTypes';

const formComponents: Record<
  RecordEntryType,
  ComponentType<RecordFormProps>
> = {
  sleep: SleepRecordForm,
  hydration: HydrationRecordForm,
  subjective_check_in: SubjectiveCheckInForm,
  daily_activity: DailyActivityRecordForm,
  workout: WorkoutRecordForm,
  body_measurement: BodyMeasurementRecordForm,
  meal: MealRecordForm,
  daily_nutrition: DailyNutritionRecordForm,
  menstrual_bleeding: MenstrualBleedingRecordForm,
  menstrual_cycle: MenstrualCycleRecordForm,
};

export const recordEntryRegistry = recordEntryOptions.map((option) => ({
  ...option,
  Form: formComponents[option.type],
}));

export function recordEntryDefinition(type: RecordEntryType) {
  return recordEntryRegistry.find((entry) => entry.type === type) ?? null;
}
