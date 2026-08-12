import {
  ApiError,
  buildApiUrl,
  createApiClient,
  normalizeBaseUrl,
} from './client';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
}

describe('ApiClient', () => {
  it('normalizes base URLs and joins paths without duplicate slashes', () => {
    expect(normalizeBaseUrl(' https://api.example.com/// ')).toBe(
      'https://api.example.com',
    );
    expect(buildApiUrl('https://api.example.com/', '/api/v1/auth/me')).toBe(
      'https://api.example.com/api/v1/auth/me',
    );
    expect(buildApiUrl('', 'api/v1/auth/me')).toBe('/api/v1/auth/me');
    expect(buildApiUrl('https://api.example.com/api', '/api/v1/auth/me')).toBe(
      'https://api.example.com/api/v1/auth/me',
    );
    expect(buildApiUrl('/api/v1', '/api/v1/auth/me')).toBe('/api/v1/auth/me');
  });

  it('sends JSON with an access token and parses the response', async () => {
    const fetchImpl: typeof fetch = vi.fn(async () =>
      jsonResponse({ user_id: 'user-1' }),
    );
    const client = createApiClient({
      baseUrl: 'https://api.example.com/',
      fetchImpl,
    });

    await expect(
      client.request('/api/v1/example', {
        method: 'POST',
        token: 'short-lived-token',
        body: { value: 4 },
      }),
    ).resolves.toEqual({ user_id: 'user-1' });

    const [url, options] = vi.mocked(fetchImpl).mock.calls[0];
    const headers = new Headers(options?.headers);
    expect(url).toBe('https://api.example.com/api/v1/example');
    expect(options?.body).toBe('{"value":4}');
    expect(headers.get('Authorization')).toBe('Bearer short-lived-token');
    expect(headers.get('Content-Type')).toBe('application/json');
  });

  it('preserves structured API error details and request IDs', async () => {
    const fetchImpl: typeof fetch = vi.fn(async () =>
      jsonResponse(
        {
          error: {
            code: 'invalid_access_token',
            message: 'Authentication credentials are invalid or expired.',
            field: null,
          },
          request_id: 'request-42',
        },
        401,
      ),
    );

    const error = await createApiClient({ fetchImpl })
      .request('/api/v1/auth/me')
      .catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      kind: 'api',
      status: 401,
      code: 'invalid_access_token',
      field: null,
      requestId: 'request-42',
    });
  });

  it('normalizes network failures without exposing the underlying error', async () => {
    const fetchImpl: typeof fetch = vi.fn(async () => {
      throw new TypeError('socket detail');
    });

    await expect(
      createApiClient({ fetchImpl }).request('/api/v1/auth/me'),
    ).rejects.toMatchObject({
      kind: 'network',
      code: 'network_error',
      message: "We couldn't reach LifeLenz. Please try again.",
    });
  });

  it('returns undefined for a successful 204 response', async () => {
    const fetchImpl: typeof fetch = vi.fn(
      async () => new Response(null, { status: 204 }),
    );

    await expect(
      createApiClient({ fetchImpl }).request<void>('/api/v1/resource', {
        method: 'DELETE',
      }),
    ).resolves.toBeUndefined();
  });

  it('rejects unexpected non-JSON responses safely', async () => {
    const fetchImpl: typeof fetch = vi.fn(
      async () =>
        new Response('<h1>server error</h1>', {
          status: 500,
          headers: { 'Content-Type': 'text/html' },
        }),
    );

    await expect(
      createApiClient({ fetchImpl }).request('/api/v1/auth/me'),
    ).rejects.toMatchObject({
      kind: 'unexpected',
      status: 500,
      message: 'LifeLenz returned an unexpected response.',
    });
  });

  it('passes abort signals through without converting cancellation to a network error', async () => {
    const abortError = new DOMException(
      'The operation was aborted.',
      'AbortError',
    );
    const fetchImpl: typeof fetch = vi.fn(async () => {
      throw abortError;
    });

    await expect(
      createApiClient({ fetchImpl }).request('/api/v1/auth/me'),
    ).rejects.toBe(abortError);
  });
});
