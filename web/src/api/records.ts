import { apiClient } from './client';
import type { WellnessRecord, WellnessRecordCreateRequest } from './types';

const RECORDS_PATH = '/api/v1/records';

export function createWellnessRecord(
  token: string,
  request: WellnessRecordCreateRequest,
  signal?: AbortSignal,
): Promise<WellnessRecord> {
  return apiClient.request<WellnessRecord>(RECORDS_PATH, {
    method: 'POST',
    token,
    body: request,
    signal,
  });
}

export function listWellnessRecords(
  token: string,
  signal?: AbortSignal,
): Promise<WellnessRecord[]> {
  return apiClient.request<WellnessRecord[]>(RECORDS_PATH, {
    method: 'GET',
    token,
    signal,
  });
}

export function getWellnessRecord(
  token: string,
  recordId: string,
  signal?: AbortSignal,
): Promise<WellnessRecord> {
  return apiClient.request<WellnessRecord>(
    `${RECORDS_PATH}/${encodeURIComponent(recordId)}`,
    { method: 'GET', token, signal },
  );
}
