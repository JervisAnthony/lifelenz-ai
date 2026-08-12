import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { useQueryClient } from '@tanstack/react-query';

import { getCurrentUser, loginAccount, registerAccount } from '../api/auth';
import { ApiError } from '../api/client';
import type { CurrentUser, LoginRequest, RegisterRequest } from '../api/types';
import {
  AuthContext,
  type AuthContextValue,
  type AuthStatus,
} from './authContext';
import { tokenStorage } from './tokenStorage';

const currentUserQueryKey = ['auth', 'current-user'] as const;

function isRejectedSession(error: unknown): error is ApiError {
  return (
    error instanceof ApiError && (error.status === 401 || error.status === 403)
  );
}

function sessionNotice(error: ApiError): string {
  if (error.code === 'inactive_account') {
    return 'This account is inactive. Please contact support if you need help.';
  }
  return 'Your session has expired. Please sign in again.';
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [accessToken, setAccessToken] = useState<string | null>(() =>
    tokenStorage.get(),
  );
  const [status, setStatus] = useState<AuthStatus>(() =>
    tokenStorage.get() ? 'loading' : 'unauthenticated',
  );
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const clearSession = useCallback(() => {
    tokenStorage.clear();
    setAccessToken(null);
    setUser(null);
    setStatus('unauthenticated');
    queryClient.removeQueries({ queryKey: currentUserQueryKey });
  }, [queryClient]);

  useEffect(() => {
    if (!accessToken) {
      return;
    }
    let active = true;
    void queryClient
      .fetchQuery({
        queryKey: currentUserQueryKey,
        queryFn: ({ signal }) => getCurrentUser(accessToken, signal),
        staleTime: 5 * 60 * 1000,
      })
      .then((currentUser) => {
        if (active) {
          setUser(currentUser);
          setStatus('authenticated');
        }
      })
      .catch((error: unknown) => {
        if (!active) {
          return;
        }
        if (isRejectedSession(error)) {
          setNotice(sessionNotice(error));
          clearSession();
        } else {
          setNotice(
            "We couldn't restore your session. Please try signing in again.",
          );
          setStatus('unauthenticated');
        }
      });
    return () => {
      active = false;
    };
  }, [accessToken, clearSession, queryClient]);

  const login = useCallback(
    async (credentials: LoginRequest): Promise<CurrentUser> => {
      setNotice(null);
      const token = await loginAccount(credentials);
      tokenStorage.set(token.access_token);
      setStatus('loading');
      try {
        const currentUser = await queryClient.fetchQuery({
          queryKey: currentUserQueryKey,
          queryFn: ({ signal }) => getCurrentUser(token.access_token, signal),
          staleTime: 5 * 60 * 1000,
        });
        setAccessToken(token.access_token);
        setUser(currentUser);
        setStatus('authenticated');
        return currentUser;
      } catch (error) {
        clearSession();
        throw error;
      }
    },
    [clearSession, queryClient],
  );

  const register = useCallback(
    (details: RegisterRequest) => registerAccount(details),
    [],
  );

  const logout = useCallback(() => {
    setNotice(null);
    clearSession();
  }, [clearSession]);

  const clearNotice = useCallback(() => setNotice(null), []);

  const value = useMemo<AuthContextValue>(
    () => ({ status, user, notice, login, register, logout, clearNotice }),
    [clearNotice, login, logout, notice, register, status, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
