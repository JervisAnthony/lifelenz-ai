import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import { createAuthValue, currentUser } from '../test/authTestUtils';
import { AuthContext } from './authContext';
import { ProfileRequiredRoute } from './ProfileRequiredRoute';

function renderGate(profileIds: string[], initialEntry = '/app') {
  render(
    <AuthContext.Provider
      value={createAuthValue({
        status: 'authenticated',
        user: { ...currentUser, profile_ids: profileIds },
      })}
    >
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/app/profile" element={<h1>Profile setup</h1>} />
          <Route element={<ProfileRequiredRoute />}>
            <Route path="/app" element={<h1>Dashboard</h1>} />
            <Route path="/app/records" element={<h1>Records</h1>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
}

describe('ProfileRequiredRoute', () => {
  it('redirects a first-time authenticated user to profile setup', () => {
    renderGate([]);
    expect(
      screen.getByRole('heading', { name: 'Profile setup' }),
    ).toBeInTheDocument();
  });

  it('renders the dashboard when the server reports an owned profile', () => {
    renderGate(['profile-1']);
    expect(
      screen.getByRole('heading', { name: 'Dashboard' }),
    ).toBeInTheDocument();
  });

  it('protects the records route with the same configured-profile gate', () => {
    renderGate([], '/app/records');
    expect(
      screen.getByRole('heading', { name: 'Profile setup' }),
    ).toBeInTheDocument();
  });
});
