import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';

import { getCurrentUser, loginAccount } from '../api/auth';
import { ApiError } from '../api/client';
import { currentUser } from '../test/authTestUtils';
import { AuthProvider } from './AuthProvider';
import { useAuth } from './authContext';
import { tokenStorage } from './tokenStorage';

vi.mock('../api/auth', () => ({
  getCurrentUser: vi.fn(),
  loginAccount: vi.fn(),
  registerAccount: vi.fn(),
}));

function Probe() {
  const { status, user, notice, login, logout } = useAuth();
  return (
    <div>
      <span data-testid="status">{status}</span>
      <span>{user?.email}</span>
      <span>{notice}</span>
      <button
        type="button"
        onClick={() =>
          void login({
            email: 'person@example.com',
            password: 'long-enough-password',
          })
        }
      >
        Log in
      </button>
      <button type="button" onClick={logout}>
        Log out
      </button>
    </div>
  );
}

function renderProvider(children: ReactNode = <Probe />) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return {
    queryClient,
    ...render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>{children}</AuthProvider>
      </QueryClientProvider>,
    ),
  };
}

describe('AuthProvider', () => {
  it('starts unauthenticated when no token exists', () => {
    renderProvider();

    expect(screen.getByTestId('status')).toHaveTextContent('unauthenticated');
    expect(getCurrentUser).not.toHaveBeenCalled();
  });

  it('restores an authenticated user from an existing token', async () => {
    tokenStorage.set('existing-token');
    vi.mocked(getCurrentUser).mockResolvedValue(currentUser);
    renderProvider();

    expect(screen.getByTestId('status')).toHaveTextContent('loading');
    expect(await screen.findByText(currentUser.email)).toBeInTheDocument();
    expect(screen.getByTestId('status')).toHaveTextContent('authenticated');
    expect(getCurrentUser).toHaveBeenCalledWith(
      'existing-token',
      expect.any(AbortSignal),
    );
  });

  it('clears an expired token during authentication bootstrap', async () => {
    tokenStorage.set('expired-token');
    vi.mocked(getCurrentUser).mockRejectedValue(
      new ApiError('expired', {
        kind: 'api',
        status: 401,
        code: 'invalid_access_token',
      }),
    );
    renderProvider();

    expect(
      await screen.findByText(
        'Your session has expired. Please sign in again.',
      ),
    ).toBeInTheDocument();
    await waitFor(() => expect(tokenStorage.get()).toBeNull());
    expect(screen.getByTestId('status')).toHaveTextContent('unauthenticated');
  });

  it('stores a new token only long enough to verify the authoritative current user', async () => {
    vi.mocked(loginAccount).mockResolvedValue({
      access_token: 'fresh-token',
      token_type: 'bearer',
      expires_in: 1800,
    });
    vi.mocked(getCurrentUser).mockResolvedValue(currentUser);
    renderProvider();

    await userEvent.click(screen.getByRole('button', { name: 'Log in' }));

    expect(await screen.findByText(currentUser.email)).toBeInTheDocument();
    expect(tokenStorage.get()).toBe('fresh-token');
    expect(screen.getByTestId('status')).toHaveTextContent('authenticated');
  });

  it('clears auth state and cached current-user data on logout', async () => {
    tokenStorage.set('existing-token');
    vi.mocked(getCurrentUser).mockResolvedValue(currentUser);
    const { queryClient } = renderProvider();
    await screen.findByText(currentUser.email);

    await userEvent.click(screen.getByRole('button', { name: 'Log out' }));

    expect(tokenStorage.get()).toBeNull();
    expect(screen.getByTestId('status')).toHaveTextContent('unauthenticated');
    expect(queryClient.getQueryData(['auth', 'current-user'])).toBeUndefined();
  });
});
