import { apiClient } from './client';
import type { WellnessSummary } from './types';

export function getWellnessSummary(
  token: string,
  signal?: AbortSignal,
): Promise<WellnessSummary> {
  return apiClient.request<WellnessSummary>('/api/v1/summary', {
    method: 'GET',
    token,
    signal,
  });
}
