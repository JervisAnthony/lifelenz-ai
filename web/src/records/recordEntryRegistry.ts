import type { ComponentType } from 'react';

import { HydrationRecordForm } from './forms/HydrationRecordForm';
import { SleepRecordForm } from './forms/SleepRecordForm';
import { SubjectiveCheckInForm } from './forms/SubjectiveCheckInForm';
import type { RecordFormProps } from './forms/formTypes';
import { recordEntryOptions, type RecordEntryType } from './recordTypes';

const formComponents: Record<
  RecordEntryType,
  ComponentType<RecordFormProps>
> = {
  sleep: SleepRecordForm,
  hydration: HydrationRecordForm,
  subjective_check_in: SubjectiveCheckInForm,
};

export const recordEntryRegistry = recordEntryOptions.map((option) => ({
  ...option,
  Form: formComponents[option.type],
}));

export function recordEntryDefinition(type: RecordEntryType) {
  return recordEntryRegistry.find((entry) => entry.type === type) ?? null;
}
