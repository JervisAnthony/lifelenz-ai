import { apiClient } from './client';
import {
  createWellnessRecord,
  deleteWellnessRecord,
  getWellnessRecord,
  listWellnessRecords,
  updateWellnessRecord,
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

  it('lists filtered history using the backend record-type and aware-range query', async () => {
    const signal = new AbortController().signal;
    const spy = vi.spyOn(apiClient, 'request').mockResolvedValue([]);

    await listWellnessRecords('token', signal, {
      recordType: 'hydration',
      start: '2026-08-10T00:00:00+05:30',
      end: '2026-08-13T00:00:00+05:30',
    });

    expect(spy).toHaveBeenCalledWith(
      '/api/v1/records?record_type=hydration&start=2026-08-10T00%3A00%3A00%2B05%3A30&end=2026-08-13T00%3A00%3A00%2B05%3A30',
      {
        method: 'GET',
        token: 'token',
        signal,
      },
    );
  });

  it('rejects an incomplete history range before making a request', async () => {
    const spy = vi.spyOn(apiClient, 'request');

    expect(() =>
      listWellnessRecords('token', undefined, {
        start: '2026-08-10T00:00:00+05:30',
      }),
    ).toThrow('start and end must be supplied together');
    expect(spy).not.toHaveBeenCalled();
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

  it('replaces an encoded record ID with the exact correction body', async () => {
    const signal = new AbortController().signal;
    const spy = vi.spyOn(apiClient, 'request').mockResolvedValue({});

    await updateWellnessRecord('token', 'record/id', request, signal);

    expect(spy).toHaveBeenCalledWith('/api/v1/records/record%2Fid', {
      method: 'PUT',
      token: 'token',
      body: request,
      signal,
    });
  });

  it('deletes an encoded record ID without sending a body', async () => {
    const signal = new AbortController().signal;
    const spy = vi.spyOn(apiClient, 'request').mockResolvedValue(undefined);

    await deleteWellnessRecord('token', 'record/id', signal);

    expect(spy).toHaveBeenCalledWith('/api/v1/records/record%2Fid', {
      method: 'DELETE',
      token: 'token',
      signal,
    });
  });

  it('propagates API failures without hiding their typed details', async () => {
    const failure = new Error('request failed');
    vi.spyOn(apiClient, 'request').mockRejectedValue(failure);

    await expect(createWellnessRecord('token', request)).rejects.toBe(failure);
  });
});
