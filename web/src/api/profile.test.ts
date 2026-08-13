import { apiClient } from './client';
import { createProfile, getProfile, updateProfile } from './profile';
import type { WellnessProfileRequest } from './types';

const request: WellnessProfileRequest = {
  time_zone: 'Asia/Kolkata',
  display_name: 'River',
  measurement_system: 'metric',
  week_start: 'monday',
  tracked_domains: ['sleep', 'hydration'],
};

describe('profile API', () => {
  it('creates a profile with the exact transport request', async () => {
    const spy = vi
      .spyOn(apiClient, 'request')
      .mockResolvedValue({ profile_id: 'profile-1' });

    await createProfile('token', request);

    expect(spy).toHaveBeenCalledWith('/api/v1/profile', {
      method: 'POST',
      token: 'token',
      body: request,
      signal: undefined,
    });
  });

  it('retrieves the authenticated primary profile with cancellation support', async () => {
    const signal = new AbortController().signal;
    const spy = vi
      .spyOn(apiClient, 'request')
      .mockResolvedValue({ profile_id: 'profile-1' });

    await getProfile('token', signal);

    expect(spy).toHaveBeenCalledWith('/api/v1/profile', {
      method: 'GET',
      token: 'token',
      signal,
    });
  });

  it('updates profile preferences without sending a profile ID', async () => {
    const spy = vi
      .spyOn(apiClient, 'request')
      .mockResolvedValue({ profile_id: 'profile-1' });

    await updateProfile('token', request);

    expect(spy).toHaveBeenCalledWith('/api/v1/profile', {
      method: 'PUT',
      token: 'token',
      body: request,
      signal: undefined,
    });
    expect(request).not.toHaveProperty('profile_id');
  });
});
