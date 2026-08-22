import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import { ApiError } from '../api/client';
import { getProfile } from '../api/profile';
import { getWellnessSummary } from '../api/summary';
import { AuthContext } from '../auth/authContext';
import { AppShell } from '../components/AppShell';
import { createAuthValue, currentUser } from '../test/authTestUtils';
import { wellnessProfile, wellnessSummary } from '../test/resourceFixtures';
import { DashboardPage } from './DashboardPage';

vi.mock('../api/profile', () => ({ getProfile: vi.fn() }));
vi.mock('../api/summary', () => ({ getWellnessSummary: vi.fn() }));

function renderDashboard(overrides = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const value = createAuthValue({
    status: 'authenticated',
    user: { ...currentUser, profile_ids: [wellnessProfile.profile_id] },
    accessToken: 'access-token',
    ...overrides,
  });
  render(
    <QueryClientProvider client={queryClient}>
      <AuthContext.Provider value={value}>
        <MemoryRouter initialEntries={['/app']}>
          <Routes>
            <Route path="/login" element={<h1>Sign in page</h1>} />
            <Route path="/app" element={<AppShell />}>
              <Route index element={<DashboardPage />} />
              <Route path="profile" element={<h1>Profile page</h1>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>
    </QueryClientProvider>,
  );
  return value;
}

describe('DashboardPage', () => {
  it('shows an honest empty state with current record actions', async () => {
    vi.mocked(getProfile).mockResolvedValue(wellnessProfile);
    vi.mocked(getWellnessSummary).mockRejectedValue(
      new ApiError('unavailable', {
        kind: 'api',
        status: 404,
        code: 'wellness_summary_unavailable',
      }),
    );
    renderDashboard();

    expect(
      await screen.findByText('Your wellness picture will appear here'),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: 'Add or review records' }),
    ).toHaveAttribute('href', '/app/records');
    expect(screen.getByRole('link', { name: 'Import CSV' })).toHaveAttribute(
      'href',
      '/app/records/import',
    );
    expect(screen.queryByText(/record entry is coming/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/calories today/i)).not.toBeInTheDocument();
  });

  it('renders profile context and descriptive analytics from real canonical summary values', async () => {
    vi.mocked(getProfile).mockResolvedValue(wellnessProfile);
    vi.mocked(getWellnessSummary).mockResolvedValue(wellnessSummary);
    renderDashboard();

    expect(
      await screen.findByRole('heading', { name: 'Welcome, River.' }),
    ).toBeInTheDocument();
    expect(screen.getByText('Sleep')).toBeInTheDocument();
    expect(screen.getByText('Hydration')).toBeInTheDocument();
    expect(
      await screen.findByRole('heading', { name: 'At a glance' }),
    ).toBeInTheDocument();
    const records = screen.getByText('Records summarized').closest('div');
    const metrics = screen.getByText('Metrics available').closest('div');
    const trends = screen.getByText('Metrics with direction').closest('div');
    expect(within(records as HTMLElement).getByText('2')).toBeInTheDocument();
    expect(within(metrics as HTMLElement).getByText('1')).toBeInTheDocument();
    expect(within(trends as HTMLElement).getByText('1')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'Water intake' }),
    ).toBeInTheDocument();
    expect(screen.getAllByText('375 mL').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText('Increasing')).toBeInTheDocument();
    expect(screen.getByText('+250 mL')).toBeInTheDocument();
    expect(screen.getByText('+100%')).toBeInTheDocument();
    expect(screen.getByText(/Based on 2 records/)).toBeInTheDocument();
    expect(
      screen.queryByText(/improving|healthy|unhealthy|worsening/i),
    ).not.toBeInTheDocument();
  });

  it('offers retry for a recoverable summary failure', async () => {
    vi.mocked(getProfile).mockResolvedValue(wellnessProfile);
    vi.mocked(getWellnessSummary).mockRejectedValue(
      new Error('server unavailable'),
    );
    renderDashboard();

    expect(
      await screen.findByRole('button', { name: 'Try summary again' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent(
      'We could not load your wellness summary.',
    );
  });

  it('offers retry without leaving the summary loading when profile loading fails', async () => {
    vi.mocked(getProfile).mockRejectedValue(new Error('profile unavailable'));
    renderDashboard();

    expect(
      await screen.findByRole('button', { name: 'Try profile again' }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/summary will be available after your profile/i),
    ).toBeInTheDocument();
    expect(
      screen.queryByText('Preparing your summary…'),
    ).not.toBeInTheDocument();
    expect(getWellnessSummary).not.toHaveBeenCalled();
  });

  it('provides real Home and Profile navigation on desktop and mobile', async () => {
    vi.mocked(getProfile).mockResolvedValue(wellnessProfile);
    vi.mocked(getWellnessSummary).mockRejectedValue(
      new ApiError('unavailable', {
        kind: 'api',
        status: 404,
        code: 'wellness_summary_unavailable',
      }),
    );
    renderDashboard();
    await screen.findByText('Your wellness picture will appear here');

    expect(
      screen.getByRole('navigation', { name: 'Application navigation' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('navigation', { name: 'Mobile application navigation' }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: 'Profile' })).toHaveLength(2);
    expect(screen.getAllByRole('link', { name: 'Records' })).toHaveLength(2);
    await userEvent.click(screen.getAllByRole('link', { name: 'Profile' })[0]);
    expect(
      screen.getByRole('heading', { name: 'Profile page' }),
    ).toBeInTheDocument();
  });

  it('clears the client session and returns to login on logout', async () => {
    vi.mocked(getProfile).mockResolvedValue(wellnessProfile);
    vi.mocked(getWellnessSummary).mockResolvedValue(wellnessSummary);
    const logout = vi.fn();
    renderDashboard({ logout });

    await userEvent.click(screen.getByRole('button', { name: 'Sign out' }));

    expect(logout).toHaveBeenCalledOnce();
    expect(
      screen.getByRole('heading', { name: 'Sign in page' }),
    ).toBeInTheDocument();
  });
});
