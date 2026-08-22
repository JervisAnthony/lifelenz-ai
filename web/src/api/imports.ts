import { apiClient } from './client';

const CSV_IMPORT_PATH = '/api/v1/imports/csv';

export const csvImportRecordTypes = [
  'sleep',
  'daily_activity',
  'hydration',
  'daily_nutrition',
  'body_measurement',
  'subjective_check_in',
] as const;

export type CsvImportRecordType = (typeof csvImportRecordTypes)[number];
export type CsvImportMode = 'validate' | 'commit';

export const csvImportRecordTypeLabels: Record<CsvImportRecordType, string> = {
  sleep: 'Sleep',
  daily_activity: 'Daily activity',
  hydration: 'Hydration',
  daily_nutrition: 'Daily nutrition',
  body_measurement: 'Body measurement',
  subjective_check_in: 'Wellness check-in',
};

export interface CsvImportRequest {
  schema_version: 1;
  record_type: CsvImportRecordType;
  mode: CsvImportMode;
  content: string;
}

export interface CsvImportIssue {
  row_number: number | null;
  field: string | null;
  code: string;
  message: string;
}

export interface CsvImportDuplicate {
  row_number: number;
  reason: 'existing_record' | 'earlier_row';
}

export interface CsvImportResponse {
  schema_version: 1;
  record_type: CsvImportRecordType;
  mode: CsvImportMode;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  duplicate_rows: number;
  ready_rows: number;
  imported_rows: number;
  can_commit: boolean;
  issues: CsvImportIssue[];
  duplicates: CsvImportDuplicate[];
}

export function importWellnessCsv(
  token: string,
  request: CsvImportRequest,
  signal?: AbortSignal,
): Promise<CsvImportResponse> {
  return apiClient.request<CsvImportResponse>(CSV_IMPORT_PATH, {
    method: 'POST',
    token,
    body: request,
    signal,
  });
}
