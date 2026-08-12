import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import { createAuthValue, currentUser } from '../test/authTestUtils';
import { AuthContext } from './authContext';
import { ProtectedRoute, PublicOnlyRoute } from './ProtectedRoute';

function renderProtected(
  status: 'loading' | 'authenticated' | 'unauthenticated',
) {
  const value = createAuthValue({
    status,
    user: status === 'authenticated' ? currentUser : null,
  });
  return render(
    <AuthContext.Provider value={value}>
      <MemoryRouter initialEntries={['/app']}>
        <Routes>
          <Route path="/login" element={<h1>Sign in page</h1>} />
          <Route element={<ProtectedRoute />}>
            <Route path="/app" element={<h1>Private home</h1>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
}

describe('ProtectedRoute', () => {
  it('shows a session loading state during authentication bootstrap', () => {
    renderProtected('loading');

    expect(screen.getByText('Restoring your session…')).toBeInTheDocument();
    expect(screen.queryByText('Private home')).not.toBeInTheDocument();
  });

  it('redirects unauthenticated visitors to login', () => {
    renderProtected('unauthenticated');

    expect(
      screen.getByRole('heading', { name: 'Sign in page' }),
    ).toBeInTheDocument();
  });

  it('renders protected content for authenticated users', () => {
    renderProtected('authenticated');

    expect(
      screen.getByRole('heading', { name: 'Private home' }),
    ).toBeInTheDocument();
  });

  it('redirects authenticated users away from public authentication routes', () => {
    const value = createAuthValue({
      status: 'authenticated',
      user: currentUser,
    });
    render(
      <AuthContext.Provider value={value}>
        <MemoryRouter initialEntries={['/login']}>
          <Routes>
            <Route element={<PublicOnlyRoute />}>
              <Route path="/login" element={<h1>Sign in page</h1>} />
            </Route>
            <Route path="/app" element={<h1>Private home</h1>} />
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>,
    );

    expect(
      screen.getByRole('heading', { name: 'Private home' }),
    ).toBeInTheDocument();
  });
});
