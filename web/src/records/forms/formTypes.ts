import type {
  WellnessRecord,
  WellnessRecordCreateRequest,
} from '../../api/types';

export interface RecordFormProps {
  isSaving: boolean;
  initialRecord?: WellnessRecord;
  onSubmit(request: WellnessRecordCreateRequest): Promise<void>;
}

export function metadata(recordedAt: string, notes: string) {
  return {
    recorded_at: recordedAt,
    source: 'manual' as const,
    notes: notes.trim() || null,
  };
}
