import { apiClient } from './client';
import type {
  AccessToken,
  CurrentUser,
  LoginRequest,
  RegisterRequest,
  UserAccount,
} from './types';

const AUTH_PATH = '/api/v1/auth';

export function registerAccount(
  request: RegisterRequest,
  signal?: AbortSignal,
): Promise<UserAccount> {
  return apiClient.request<UserAccount>(`${AUTH_PATH}/register`, {
    method: 'POST',
    body: request,
    signal,
  });
}

export function loginAccount(
  request: LoginRequest,
  signal?: AbortSignal,
): Promise<AccessToken> {
  return apiClient.request<AccessToken>(`${AUTH_PATH}/login`, {
    method: 'POST',
    body: request,
    signal,
  });
}

export function getCurrentUser(
  token: string,
  signal?: AbortSignal,
): Promise<CurrentUser> {
  return apiClient.request<CurrentUser>(`${AUTH_PATH}/me`, {
    method: 'GET',
    token,
    signal,
  });
}
