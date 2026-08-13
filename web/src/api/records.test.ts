import { apiClient } from './client';
import {
  createWellnessRecord,
  getWellnessRecord,
  listWellnessRecords,
} from './records';
import type { HydrationRecordCreateRequest } from './types';

const request: HydrationRecordCreateRequest = {
  record_type: 'hydration',
  metadata: {
    recorded_at: '2026-08-14T10:30:00+05:30',
    source: 'manual',
    notes: null,
  },
  data: {
    volume_milliliters: 350,
    beverage_type: 'water',
    caffeine_milligrams: null,
  },
};

describe('records API', () => {
  it('creates an authenticated record with the exact request body', async () => {
    const spy = vi.spyOn(apiClient, 'request').mockResolvedValue({});

    await createWellnessRecord('token', request);

    expect(spy).toHaveBeenCalledWith('/api/v1/records', {
      method: 'POST',
      token: 'token',
      body: request,
      signal: undefined,
    });
  });

  it('lists records with cancellation support', async () => {
    const signal = new AbortController().signal;
    const spy = vi.spyOn(apiClient, 'request').mockResolvedValue([]);

    await listWellnessRecords('token', signal);

    expect(spy).toHaveBeenCalledWith('/api/v1/records', {
      method: 'GET',
      token: 'token',
      signal,
    });
  });

  it('retrieves an encoded server-controlled record ID', async () => {
    const spy = vi.spyOn(apiClient, 'request').mockResolvedValue({});

    await getWellnessRecord('token', 'record/id');

    expect(spy).toHaveBeenCalledWith('/api/v1/records/record%2Fid', {
      method: 'GET',
      token: 'token',
      signal: undefined,
    });
  });

  it('propagates API failures without hiding their typed details', async () => {
    const failure = new Error('request failed');
    vi.spyOn(apiClient, 'request').mockRejectedValue(failure);

    await expect(createWellnessRecord('token', request)).rejects.toBe(failure);
  });
});
