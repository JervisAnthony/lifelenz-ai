import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import { ApiError } from '../api/client';
import { createProfile, getProfile, updateProfile } from '../api/profile';
import { AuthContext } from '../auth/authContext';
import { createAuthValue, currentUser } from '../test/authTestUtils';
import { wellnessProfile } from '../test/resourceFixtures';
import { ProfilePage } from './ProfilePage';

vi.mock('../api/profile', () => ({
  createProfile: vi.fn(),
  getProfile: vi.fn(),
  updateProfile: vi.fn(),
}));

function renderProfile(hasProfile: boolean, overrides = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const auth = createAuthValue({
    status: 'authenticated',
    user: {
      ...currentUser,
      profile_ids: hasProfile ? [wellnessProfile.profile_id] : [],
    },
    accessToken: 'access-token',
    refreshCurrentUser: vi.fn(async () => ({
      ...currentUser,
      profile_ids: [wellnessProfile.profile_id],
    })),
    ...overrides,
  });
  render(
    <QueryClientProvider client={queryClient}>
      <AuthContext.Provider value={auth}>
        <MemoryRouter initialEntries={['/app/profile']}>
          <Routes>
            <Route path="/app/profile" element={<ProfilePage />} />
            <Route path="/app" element={<h1>Wellness dashboard</h1>} />
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>
    </QueryClientProvider>,
  );
  return { auth, queryClient };
}

describe('ProfilePage', () => {
  it('renders an accessible first-time setup form from authoritative no-profile state', () => {
    renderProfile(false);

    expect(
      screen.getByRole('heading', { name: 'Set up your wellness profile' }),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText('Display name (optional)'),
    ).toBeInTheDocument();
    expect(screen.getByLabelText('Time zone')).toBeRequired();
    expect(
      screen.getByRole('group', { name: /measurement preference/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('group', { name: /areas you want to track/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Complete setup' }),
    ).toBeEnabled();
  });

  it('creates a profile, refreshes current user, and navigates to the dashboard', async () => {
    vi.mocked(createProfile).mockResolvedValue(wellnessProfile);
    const { auth } = renderProfile(false);
    const user = userEvent.setup();

    await user.clear(screen.getByLabelText('Time zone'));
    await user.type(screen.getByLabelText('Time zone'), 'Asia/Kolkata');
    await user.type(screen.getByLabelText('Display name (optional)'), 'River');
    await user.click(screen.getByLabelText(/^Sleep/));
    await user.click(screen.getByLabelText(/^Hydration/));
    await user.click(screen.getByRole('button', { name: 'Complete setup' }));

    expect(createProfile).toHaveBeenCalledWith('access-token', {
      time_zone: 'Asia/Kolkata',
      display_name: 'River',
      measurement_system: 'metric',
      week_start: 'monday',
      tracked_domains: ['sleep', 'hydration'],
    });
    expect(auth.refreshCurrentUser).toHaveBeenCalledOnce();
    expect(
      await screen.findByRole('heading', { name: 'Wellness dashboard' }),
    ).toBeInTheDocument();
  });

  it('loads and updates existing preferences without exposing the profile ID', async () => {
    vi.mocked(getProfile).mockResolvedValue(wellnessProfile);
    vi.mocked(updateProfile).mockResolvedValue({
      ...wellnessProfile,
      week_start: 'sunday',
    });
    renderProfile(true);
    const user = userEvent.setup();

    expect(
      await screen.findByRole('heading', { name: 'Profile preferences' }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText('Display name (optional)')).toHaveValue(
      'River',
    );
    expect(
      screen.queryByText(wellnessProfile.profile_id),
    ).not.toBeInTheDocument();
    await user.click(screen.getByLabelText('Sunday'));
    await user.click(screen.getByRole('button', { name: 'Save preferences' }));

    expect(updateProfile).toHaveBeenCalledWith(
      'access-token',
      expect.objectContaining({ week_start: 'sunday' }),
    );
    expect(
      await screen.findByText('Profile preferences saved.'),
    ).toBeInTheDocument();
  });

  it('recovers when create reports that a profile already exists', async () => {
    vi.mocked(createProfile).mockRejectedValue(
      new ApiError('already exists', {
        kind: 'api',
        status: 409,
        code: 'profile_already_exists',
      }),
    );
    vi.mocked(getProfile).mockResolvedValue(wellnessProfile);
    const { auth } = renderProfile(false);

    await userEvent.click(
      screen.getByRole('button', { name: 'Complete setup' }),
    );

    await waitFor(() =>
      expect(getProfile).toHaveBeenCalledWith(
        'access-token',
        expect.any(AbortSignal),
      ),
    );
    expect(auth.refreshCurrentUser).toHaveBeenCalledOnce();
    expect(
      await screen.findByText('Your existing profile is ready to edit.'),
    ).toBeInTheDocument();
  });

  it('switches safely to setup when an expected profile is not configured', async () => {
    vi.mocked(getProfile).mockRejectedValue(
      new ApiError('missing', {
        kind: 'api',
        status: 404,
        code: 'profile_not_configured',
      }),
    );
    renderProfile(true);

    expect(
      await screen.findByRole('heading', {
        name: 'Set up your wellness profile',
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Complete setup' }),
    ).toBeEnabled();
  });
});
