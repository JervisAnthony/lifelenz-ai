import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import { AuthContext } from '../auth/authContext';
import { ProfileRequiredRoute } from '../auth/ProfileRequiredRoute';
import { ProtectedRoute } from '../auth/ProtectedRoute';
import { createAuthValue, currentUser } from '../test/authTestUtils';
import { ImportPage } from './ImportPage';

function renderImport(
  status: 'authenticated' | 'unauthenticated',
  hasProfile: boolean,
) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const auth = createAuthValue({
    status,
    user:
      status === 'authenticated'
        ? {
            ...currentUser,
            profile_ids: hasProfile ? ['synthetic-profile'] : [],
          }
        : null,
    accessToken: status === 'authenticated' ? 'access-token' : null,
  });
  render(
    <QueryClientProvider client={queryClient}>
      <AuthContext.Provider value={auth}>
        <MemoryRouter initialEntries={['/app/records/import']}>
          <Routes>
            <Route path="/login" element={<h1>Login destination</h1>} />
            <Route path="/app/profile" element={<h1>Profile destination</h1>} />
            <Route element={<ProtectedRoute />}>
              <Route element={<ProfileRequiredRoute />}>
                <Route path="/app/records/import" element={<ImportPage />} />
              </Route>
            </Route>
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>
    </QueryClientProvider>,
  );
}

describe('ImportPage routing', () => {
  it('renders the import workflow with clear Records navigation for configured users', () => {
    renderImport('authenticated', true);
    expect(
      screen.getByRole('heading', { name: 'Import wellness records' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: 'Back to Records' }),
    ).toHaveAttribute('href', '/app/records');
  });

  it('requires authentication', () => {
    renderImport('unauthenticated', false);
    expect(
      screen.getByRole('heading', { name: 'Login destination' }),
    ).toBeInTheDocument();
  });

  it('requires a configured profile through the shared gate', () => {
    renderImport('authenticated', false);
    expect(
      screen.getByRole('heading', { name: 'Profile destination' }),
    ).toBeInTheDocument();
  });
});
