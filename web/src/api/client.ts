import type { ApiErrorEnvelope } from './types';

export type ApiErrorKind = 'api' | 'network' | 'unexpected';

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number | null;
  readonly code: string;
  readonly field: string | null;
  readonly requestId: string | null;

  constructor(
    message: string,
    options: {
      kind: ApiErrorKind;
      status?: number;
      code?: string;
      field?: string | null;
      requestId?: string | null;
    },
  ) {
    super(message);
    this.name = 'ApiError';
    this.kind = options.kind;
    this.status = options.status ?? null;
    this.code = options.code ?? 'unexpected_error';
    this.field = options.field ?? null;
    this.requestId = options.requestId ?? null;
  }
}

interface ApiRequestOptions extends Omit<RequestInit, 'body' | 'headers'> {
  body?: unknown;
  headers?: HeadersInit;
  token?: string | null;
}

interface ApiClientOptions {
  baseUrl?: string;
  fetchImpl?: typeof fetch;
}

export interface ApiClient {
  request<T>(path: string, options?: ApiRequestOptions): Promise<T>;
}

export function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.trim().replace(/\/+$/, '');
}

export function buildApiUrl(baseUrl: string, path: string): string {
  const normalizedBase = normalizeBaseUrl(baseUrl);
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  for (const apiPrefix of ['/api/v1', '/api']) {
    if (
      normalizedBase.endsWith(apiPrefix) &&
      (normalizedPath === apiPrefix ||
        normalizedPath.startsWith(`${apiPrefix}/`))
    ) {
      return `${normalizedBase}${normalizedPath.slice(apiPrefix.length)}`;
    }
  }
  return `${normalizedBase}${normalizedPath}`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function parseErrorEnvelope(value: unknown): ApiErrorEnvelope | null {
  if (!isRecord(value) || !isRecord(value.error)) {
    return null;
  }

  const { error, request_id: requestId } = value;
  if (
    typeof error.code !== 'string' ||
    typeof error.message !== 'string' ||
    (error.field !== null && typeof error.field !== 'string') ||
    typeof requestId !== 'string'
  ) {
    return null;
  }

  return {
    error: {
      code: error.code,
      message: error.message,
      field: error.field,
    },
    request_id: requestId,
  };
}

async function readJson(response: Response): Promise<unknown> {
  const contentType = response.headers.get('content-type') ?? '';
  const body = await response.text();
  if (!body) {
    return undefined;
  }
  if (!contentType.toLowerCase().includes('application/json')) {
    throw new ApiError('LifeLenz returned an unexpected response.', {
      kind: 'unexpected',
      status: response.status,
    });
  }
  try {
    return JSON.parse(body) as unknown;
  } catch {
    throw new ApiError('LifeLenz returned an unexpected response.', {
      kind: 'unexpected',
      status: response.status,
    });
  }
}

export function createApiClient(options: ApiClientOptions = {}): ApiClient {
  const baseUrl = normalizeBaseUrl(
    options.baseUrl ?? import.meta.env.VITE_LIFELENZ_API_BASE_URL ?? '',
  );
  const fetchImpl = options.fetchImpl ?? globalThis.fetch;

  return {
    async request<T>(
      path: string,
      requestOptions: ApiRequestOptions = {},
    ): Promise<T> {
      const {
        body,
        headers: customHeaders,
        token,
        ...fetchOptions
      } = requestOptions;
      const headers = new Headers(customHeaders);
      headers.set('Accept', 'application/json');
      if (body !== undefined) {
        headers.set('Content-Type', 'application/json');
      }
      if (token) {
        headers.set('Authorization', `Bearer ${token}`);
      }

      let response: Response;
      try {
        response = await fetchImpl(buildApiUrl(baseUrl, path), {
          ...fetchOptions,
          headers,
          body: body === undefined ? undefined : JSON.stringify(body),
        });
      } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') {
          throw error;
        }
        throw new ApiError("We couldn't reach LifeLenz. Please try again.", {
          kind: 'network',
          code: 'network_error',
        });
      }

      if (response.status === 204) {
        if (!response.ok) {
          throw new ApiError('LifeLenz could not complete the request.', {
            kind: 'unexpected',
            status: response.status,
          });
        }
        return undefined as T;
      }

      const payload = await readJson(response);
      if (!response.ok) {
        const envelope = parseErrorEnvelope(payload);
        if (envelope) {
          throw new ApiError(envelope.error.message, {
            kind: 'api',
            status: response.status,
            code: envelope.error.code,
            field: envelope.error.field,
            requestId: envelope.request_id,
          });
        }
        throw new ApiError('LifeLenz could not complete the request.', {
          kind: 'unexpected',
          status: response.status,
        });
      }

      if (payload === undefined) {
        throw new ApiError('LifeLenz returned an unexpected response.', {
          kind: 'unexpected',
          status: response.status,
        });
      }
      return payload as T;
    },
  };
}

export const apiClient = createApiClient();
