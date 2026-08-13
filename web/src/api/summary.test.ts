import { apiClient } from './client';
import { getWellnessSummary } from './summary';

describe('summary API', () => {
  it('retrieves the default authenticated wellness summary', async () => {
    const signal = new AbortController().signal;
    const spy = vi.spyOn(apiClient, 'request').mockResolvedValue({
      metrics: [],
      time_range: null,
      generated_from_record_count: 0,
    });

    await getWellnessSummary('token', signal);

    expect(spy).toHaveBeenCalledWith('/api/v1/summary', {
      method: 'GET',
      token: 'token',
      signal,
    });
  });
});
