import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import { AuthContext } from '../auth/authContext';
import { AppShell } from '../components/AppShell';
import { createAuthValue, currentUser } from '../test/authTestUtils';
import { DashboardPage } from './DashboardPage';

function renderDashboard(overrides = {}) {
  const value = createAuthValue({
    status: 'authenticated',
    user: currentUser,
    ...overrides,
  });
  render(
    <AuthContext.Provider value={value}>
      <MemoryRouter initialEntries={['/app']}>
        <Routes>
          <Route path="/login" element={<h1>Sign in page</h1>} />
          <Route path="/app" element={<AppShell />}>
            <Route index element={<DashboardPage />} />
          </Route>
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
  return value;
}

describe('DashboardPage', () => {
  it('shows safe current-user details and clearly labels unimplemented features', () => {
    renderDashboard();

    expect(screen.getAllByText(currentUser.email).length).toBeGreaterThan(0);
    expect(screen.getByText('Not configured yet')).toBeInTheDocument();
    expect(
      screen.getAllByText('Coming next', { selector: 'span' }),
    ).toHaveLength(4);
    expect(screen.queryByText(/calories today/i)).not.toBeInTheDocument();
    expect(
      screen.getByRole('navigation', { name: 'Application navigation' }),
    ).toBeInTheDocument();
  });

  it('clears the client session and returns to login on logout', async () => {
    const logout = vi.fn();
    renderDashboard({ logout });

    await userEvent.click(screen.getByRole('button', { name: 'Sign out' }));

    expect(logout).toHaveBeenCalledOnce();
    expect(
      screen.getByRole('heading', { name: 'Sign in page' }),
    ).toBeInTheDocument();
  });
});
