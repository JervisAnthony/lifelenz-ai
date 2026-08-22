import { ApiError, apiClient } from './client';
import {
  csvImportRecordTypes,
  importWellnessCsv,
  type CsvImportRequest,
  type CsvImportResponse,
} from './imports';

const content = 'recorded_at,volume_value\n2026-08-20T10:00:00+05:30,500\n';

function request(mode: CsvImportRequest['mode']): CsvImportRequest {
  return {
    schema_version: 1,
    record_type: 'hydration',
    mode,
    content,
  };
}

const response: CsvImportResponse = {
  schema_version: 1,
  record_type: 'hydration',
  mode: 'validate',
  total_rows: 1,
  valid_rows: 1,
  invalid_rows: 0,
  duplicate_rows: 0,
  ready_rows: 1,
  imported_rows: 0,
  can_commit: true,
  issues: [],
  duplicates: [],
};

describe('CSV imports API', () => {
  it.each(['validate', 'commit'] as const)(
    'sends the exact authenticated %s request with cancellation support',
    async (mode) => {
      const signal = new AbortController().signal;
      const spy = vi.spyOn(apiClient, 'request').mockResolvedValue(response);
      const body = request(mode);

      await expect(
        importWellnessCsv('access-token', body, signal),
      ).resolves.toBe(response);

      expect(spy).toHaveBeenCalledWith('/api/v1/imports/csv', {
        method: 'POST',
        token: 'access-token',
        body,
        signal,
      });
    },
  );

  it('propagates structured API failures unchanged', async () => {
    const failure = new ApiError('Synthetic validation failure', {
      kind: 'api',
      status: 422,
      code: 'request_validation_error',
    });
    vi.spyOn(apiClient, 'request').mockRejectedValue(failure);

    await expect(importWellnessCsv('token', request('validate'))).rejects.toBe(
      failure,
    );
  });

  it('keeps the six supported CSV v1 categories exhaustive', () => {
    expect(csvImportRecordTypes).toEqual([
      'sleep',
      'daily_activity',
      'hydration',
      'daily_nutrition',
      'body_measurement',
      'subjective_check_in',
    ]);
  });
});
