import { apiClient } from './client';
import type { WellnessProfile, WellnessProfileRequest } from './types';

const PROFILE_PATH = '/api/v1/profile';

export function createProfile(
  token: string,
  request: WellnessProfileRequest,
  signal?: AbortSignal,
): Promise<WellnessProfile> {
  return apiClient.request<WellnessProfile>(PROFILE_PATH, {
    method: 'POST',
    token,
    body: request,
    signal,
  });
}

export function getProfile(
  token: string,
  signal?: AbortSignal,
): Promise<WellnessProfile> {
  return apiClient.request<WellnessProfile>(PROFILE_PATH, {
    method: 'GET',
    token,
    signal,
  });
}

export function updateProfile(
  token: string,
  request: WellnessProfileRequest,
  signal?: AbortSignal,
): Promise<WellnessProfile> {
  return apiClient.request<WellnessProfile>(PROFILE_PATH, {
    method: 'PUT',
    token,
    body: request,
    signal,
  });
}
