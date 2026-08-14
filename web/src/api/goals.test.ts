import { apiClient } from './client';
import {
  createWellnessGoal,
  deleteWellnessGoal,
  getWellnessGoal,
  listWellnessGoals,
  updateWellnessGoal,
} from './goals';
import type { WellnessGoalRequest } from './types';

const request: WellnessGoalRequest = {
  target: { metric: 'steps', value: 1234, unit: 'count' },
  direction: 'at_least',
  status: 'draft',
  start_date: null,
  target_date: null,
  title: null,
  description: null,
};

describe('goals API', () => {
  it('lists authenticated goals with cancellation support', async () => {
    const signal = new AbortController().signal;
    const spy = vi.spyOn(apiClient, 'request').mockResolvedValue([]);
    await listWellnessGoals('token', signal);
    expect(spy).toHaveBeenCalledWith('/api/v1/goals', {
      method: 'GET',
      token: 'token',
      signal,
    });
  });

  it('creates a goal with only the user-controlled request body', async () => {
    const spy = vi.spyOn(apiClient, 'request').mockResolvedValue({});
    await createWellnessGoal('token', request);
    expect(spy).toHaveBeenCalledWith('/api/v1/goals', {
      method: 'POST',
      token: 'token',
      body: request,
      signal: undefined,
    });
    expect(request).not.toHaveProperty('goal_id');
    expect(request).not.toHaveProperty('profile_id');
  });

  it('gets an encoded server-controlled goal ID', async () => {
    const spy = vi.spyOn(apiClient, 'request').mockResolvedValue({});
    await getWellnessGoal('token', 'goal/id');
    expect(spy).toHaveBeenCalledWith('/api/v1/goals/goal%2Fid', {
      method: 'GET',
      token: 'token',
      signal: undefined,
    });
  });

  it('replaces a goal using PUT and the complete request body', async () => {
    const spy = vi.spyOn(apiClient, 'request').mockResolvedValue({});
    await updateWellnessGoal('token', 'goal/id', request);
    expect(spy).toHaveBeenCalledWith('/api/v1/goals/goal%2Fid', {
      method: 'PUT',
      token: 'token',
      body: request,
      signal: undefined,
    });
  });

  it('deletes a goal and propagates typed client failures', async () => {
    const spy = vi.spyOn(apiClient, 'request').mockResolvedValue(undefined);
    await deleteWellnessGoal('token', 'goal/id');
    expect(spy).toHaveBeenCalledWith('/api/v1/goals/goal%2Fid', {
      method: 'DELETE',
      token: 'token',
      signal: undefined,
    });
    const failure = new Error('request failed');
    spy.mockRejectedValue(failure);
    await expect(deleteWellnessGoal('token', 'goal')).rejects.toBe(failure);
  });
});
