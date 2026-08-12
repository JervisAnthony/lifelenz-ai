import { createContext, useContext } from 'react';

import type {
  CurrentUser,
  LoginRequest,
  RegisterRequest,
  UserAccount,
} from '../api/types';

export type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated';

export interface AuthContextValue {
  status: AuthStatus;
  user: CurrentUser | null;
  notice: string | null;
  login(credentials: LoginRequest): Promise<CurrentUser>;
  register(details: RegisterRequest): Promise<UserAccount>;
  logout(): void;
  clearNotice(): void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
