import { apiClient } from './client';
import type {
  WellnessRecord,
  WellnessRecordCreateRequest,
  WellnessRecordType,
} from './types';

const RECORDS_PATH = '/api/v1/records';

export interface WellnessRecordListFilters {
  recordType?: WellnessRecordType;
  start?: string;
  end?: string;
}

function recordsListPath(filters: WellnessRecordListFilters): string {
  if ((filters.start === undefined) !== (filters.end === undefined)) {
    throw new Error('Record history start and end must be supplied together.');
  }

  const parameters = new URLSearchParams();
  if (filters.recordType) {
    parameters.set('record_type', filters.recordType);
  }
  if (filters.start && filters.end) {
    parameters.set('start', filters.start);
    parameters.set('end', filters.end);
  }

  const query = parameters.toString();
  return query ? `${RECORDS_PATH}?${query}` : RECORDS_PATH;
}

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
  filters: WellnessRecordListFilters = {},
): Promise<WellnessRecord[]> {
  return apiClient.request<WellnessRecord[]>(recordsListPath(filters), {
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

export function updateWellnessRecord(
  token: string,
  recordId: string,
  request: WellnessRecordCreateRequest,
  signal?: AbortSignal,
): Promise<WellnessRecord> {
  return apiClient.request<WellnessRecord>(
    `${RECORDS_PATH}/${encodeURIComponent(recordId)}`,
    {
      method: 'PUT',
      token,
      body: request,
      signal,
    },
  );
}

export function deleteWellnessRecord(
  token: string,
  recordId: string,
  signal?: AbortSignal,
): Promise<void> {
  return apiClient.request<void>(
    `${RECORDS_PATH}/${encodeURIComponent(recordId)}`,
    {
      method: 'DELETE',
      token,
      signal,
    },
  );
}
