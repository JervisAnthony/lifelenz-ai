import { apiClient } from './client';
import type { WellnessGoal, WellnessGoalRequest } from './types';

const GOALS_PATH = '/api/v1/goals';

export function listWellnessGoals(
  token: string,
  signal?: AbortSignal,
): Promise<WellnessGoal[]> {
  return apiClient.request<WellnessGoal[]>(GOALS_PATH, {
    method: 'GET',
    token,
    signal,
  });
}

export function createWellnessGoal(
  token: string,
  request: WellnessGoalRequest,
  signal?: AbortSignal,
): Promise<WellnessGoal> {
  return apiClient.request<WellnessGoal>(GOALS_PATH, {
    method: 'POST',
    token,
    body: request,
    signal,
  });
}

export function getWellnessGoal(
  token: string,
  goalId: string,
  signal?: AbortSignal,
): Promise<WellnessGoal> {
  return apiClient.request<WellnessGoal>(
    `${GOALS_PATH}/${encodeURIComponent(goalId)}`,
    { method: 'GET', token, signal },
  );
}

export function updateWellnessGoal(
  token: string,
  goalId: string,
  request: WellnessGoalRequest,
  signal?: AbortSignal,
): Promise<WellnessGoal> {
  return apiClient.request<WellnessGoal>(
    `${GOALS_PATH}/${encodeURIComponent(goalId)}`,
    { method: 'PUT', token, body: request, signal },
  );
}

export function deleteWellnessGoal(
  token: string,
  goalId: string,
  signal?: AbortSignal,
): Promise<void> {
  return apiClient.request<void>(
    `${GOALS_PATH}/${encodeURIComponent(goalId)}`,
    { method: 'DELETE', token, signal },
  );
}
