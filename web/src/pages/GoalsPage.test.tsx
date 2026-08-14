import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import { ApiError } from '../api/client';
import {
  createWellnessGoal,
  deleteWellnessGoal,
  listWellnessGoals,
  updateWellnessGoal,
} from '../api/goals';
import { AuthContext } from '../auth/authContext';
import { AppShell } from '../components/AppShell';
import { createAuthValue, currentUser } from '../test/authTestUtils';
import {
  updatedWellnessGoal,
  wellnessGoal,
  wellnessProfile,
} from '../test/resourceFixtures';
import { GoalsPage } from './GoalsPage';

vi.mock('../api/goals', () => ({
  createWellnessGoal: vi.fn(),
  deleteWellnessGoal: vi.fn(),
  getWellnessGoal: vi.fn(),
  listWellnessGoals: vi.fn(),
  updateWellnessGoal: vi.fn(),
}));

function renderGoals() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  const auth = createAuthValue({
    status: 'authenticated',
    user: { ...currentUser, profile_ids: [wellnessProfile.profile_id] },
    accessToken: 'access-token',
  });
  render(
    <QueryClientProvider client={queryClient}>
      <AuthContext.Provider value={auth}>
        <MemoryRouter initialEntries={['/app/goals']}>
          <Routes>
            <Route path="/app" element={<AppShell />}>
              <Route index element={<h1>Home page</h1>} />
              <Route path="records" element={<h1>Records page</h1>} />
              <Route path="goals" element={<GoalsPage />} />
              <Route path="profile" element={<h1>Profile page</h1>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>
    </QueryClientProvider>,
  );
  return { queryClient };
}

function goalCard() {
  return screen.getByRole('article', {
    name: wellnessGoal.title as string,
  });
}

describe('GoalsPage', () => {
  it('shows an accessible loading state', () => {
    vi.mocked(listWellnessGoals).mockReturnValue(new Promise(() => undefined));
    renderGoals();
    expect(screen.getByText('Loading wellness goals…')).toHaveAttribute(
      'role',
      'status',
    );
  });

  it('shows an honest empty state and four-destination active navigation', async () => {
    vi.mocked(listWellnessGoals).mockResolvedValue([]);
    renderGoals();
    expect(
      await screen.findByText('No wellness goals yet.'),
    ).toBeInTheDocument();
    expect(screen.getByText(/without creating a goal/i)).toBeInTheDocument();
    const desktop = screen.getByRole('navigation', {
      name: 'Application navigation',
    });
    expect(within(desktop).getAllByRole('link')).toHaveLength(4);
    expect(within(desktop).getByRole('link', { name: 'Goals' })).toHaveClass(
      'active',
    );
    const mobile = screen.getByRole('navigation', {
      name: 'Mobile application navigation',
    });
    expect(within(mobile).getAllByRole('link')).toHaveLength(4);
  });

  it('renders server order with friendly neutral goal values', async () => {
    vi.mocked(listWellnessGoals).mockResolvedValue([
      wellnessGoal,
      {
        ...updatedWellnessGoal,
        goal_id: 'f6f91ed2-9d67-4c7e-819b-31df6b4e5cd8',
      },
    ]);
    renderGoals();
    const cards = await screen.findAllByRole('article');
    expect(cards).toHaveLength(2);
    expect(within(cards[0]).getByText('Water intake')).toBeInTheDocument();
    expect(within(cards[0]).getByText('At least')).toBeInTheDocument();
    expect(within(cards[0]).getByText(/1,234 milliliters/)).toBeInTheDocument();
    expect(screen.queryByText('water_intake')).not.toBeInTheDocument();
    expect(
      screen.queryByText(/on track|suggested target|healthy target/i),
    ).toBeNull();
  });

  it('offers retry after a list failure', async () => {
    vi.mocked(listWellnessGoals)
      .mockRejectedValueOnce(new Error('offline'))
      .mockResolvedValue([]);
    renderGoals();
    const user = userEvent.setup();
    await user.click(
      await screen.findByRole('button', { name: 'Try goals again' }),
    );
    expect(
      await screen.findByText('No wellness goals yet.'),
    ).toBeInTheDocument();
    expect(listWellnessGoals).toHaveBeenCalledTimes(2);
  });

  it('creates from user fields, refetches, announces success, and resets', async () => {
    vi.mocked(listWellnessGoals)
      .mockResolvedValueOnce([])
      .mockResolvedValue([wellnessGoal]);
    vi.mocked(createWellnessGoal).mockResolvedValue(wellnessGoal);
    renderGoals();
    const user = userEvent.setup();
    await screen.findByText('No wellness goals yet.');
    await user.selectOptions(screen.getByLabelText('Metric'), 'water_intake');
    await user.type(screen.getByLabelText('Target value'), '1234');
    await user.selectOptions(screen.getByLabelText('Status'), 'active');
    await user.click(screen.getByRole('button', { name: 'Create goal' }));

    expect(
      await screen.findByText('Wellness goal created.'),
    ).toBeInTheDocument();
    expect(
      await screen.findByText(wellnessGoal.title as string),
    ).toBeInTheDocument();
    expect(createWellnessGoal).toHaveBeenCalledWith('access-token', {
      target: { metric: 'water_intake', value: 1234, unit: 'milliliters' },
      direction: 'at_least',
      status: 'active',
      start_date: null,
      target_date: null,
      title: null,
      description: null,
    });
    expect(screen.getByLabelText('Target value')).toHaveValue(null);
  });

  it('preserves create input and sanitizes a failed create message', async () => {
    vi.mocked(listWellnessGoals).mockResolvedValue([]);
    vi.mocked(createWellnessGoal).mockRejectedValue(
      new ApiError('internal target detail', {
        kind: 'api',
        status: 422,
        code: 'domain_validation_error',
      }),
    );
    renderGoals();
    const user = userEvent.setup();
    await screen.findByText('No wellness goals yet.');
    await user.type(screen.getByLabelText('Target value'), '12');
    await user.click(screen.getByRole('button', { name: 'Create goal' }));
    expect(await screen.findByText(/review the details/i)).toBeInTheDocument();
    expect(screen.getByLabelText('Target value')).toHaveValue(12);
    expect(
      screen.queryByText('internal target detail'),
    ).not.toBeInTheDocument();
  });

  it('enters and cancels isolated edit state without a mutation', async () => {
    vi.mocked(listWellnessGoals).mockResolvedValue([wellnessGoal]);
    renderGoals();
    const user = userEvent.setup();
    await user.click(
      await screen.findByRole('button', {
        name: `Edit ${wellnessGoal.title}`,
      }),
    );
    const card = goalCard();
    const target = within(card).getByLabelText('Target value');
    await user.clear(target);
    await user.type(target, '2345');
    await user.click(within(card).getByRole('button', { name: 'Cancel edit' }));
    expect(updateWellnessGoal).not.toHaveBeenCalled();
    expect(
      within(goalCard()).getByText(/1,234 milliliters/),
    ).toBeInTheDocument();
    expect(screen.getByLabelText('Target value')).toHaveValue(null);
  });

  it('updates with full PUT data and exits after server-authoritative refetch', async () => {
    vi.mocked(listWellnessGoals)
      .mockResolvedValueOnce([wellnessGoal])
      .mockResolvedValue([updatedWellnessGoal]);
    vi.mocked(updateWellnessGoal).mockResolvedValue(updatedWellnessGoal);
    renderGoals();
    const user = userEvent.setup();
    await user.click(
      await screen.findByRole('button', {
        name: `Edit ${wellnessGoal.title}`,
      }),
    );
    const card = goalCard();
    const target = within(card).getByLabelText('Target value');
    await user.clear(target);
    await user.type(target, '2345');
    await user.selectOptions(within(card).getByLabelText('Status'), 'paused');
    await user.click(
      within(card).getByRole('button', { name: 'Save goal changes' }),
    );

    expect(
      await screen.findByText('Wellness goal updated.'),
    ).toBeInTheDocument();
    expect(
      await screen.findByText('Updated synthetic target'),
    ).toBeInTheDocument();
    expect(updateWellnessGoal).toHaveBeenCalledWith(
      'access-token',
      wellnessGoal.goal_id,
      expect.objectContaining({
        target: expect.objectContaining({ value: 2345 }),
        status: 'paused',
      }),
    );
  });

  it('keeps edit controls and input after update failure', async () => {
    vi.mocked(listWellnessGoals).mockResolvedValue([wellnessGoal]);
    vi.mocked(updateWellnessGoal).mockRejectedValue(new Error('offline'));
    renderGoals();
    const user = userEvent.setup();
    await user.click(
      await screen.findByRole('button', {
        name: `Edit ${wellnessGoal.title}`,
      }),
    );
    const card = goalCard();
    const target = within(card).getByLabelText('Target value');
    await user.clear(target);
    await user.type(target, '3456');
    await user.click(
      within(card).getByRole('button', { name: 'Save goal changes' }),
    );
    expect(
      await within(card).findByText(/couldn't update/i),
    ).toBeInTheDocument();
    expect(within(card).getByLabelText('Target value')).toHaveValue(3456);
  });

  it('requires deliberate delete confirmation and supports cancellation', async () => {
    vi.mocked(listWellnessGoals).mockResolvedValue([wellnessGoal]);
    renderGoals();
    const user = userEvent.setup();
    await user.click(
      await screen.findByRole('button', {
        name: `Delete ${wellnessGoal.title}`,
      }),
    );
    const confirmation = screen.getByRole('group', {
      name: `Delete ${wellnessGoal.title}`,
    });
    expect(
      within(confirmation).getByRole('button', { name: 'Confirm delete' }),
    ).toBeInTheDocument();
    await user.click(
      within(confirmation).getByRole('button', { name: 'Cancel delete' }),
    );
    expect(deleteWellnessGoal).not.toHaveBeenCalled();
    expect(goalCard()).toBeInTheDocument();
  });

  it('deletes only after confirmation and server-authoritative refetch', async () => {
    vi.mocked(listWellnessGoals)
      .mockResolvedValueOnce([wellnessGoal])
      .mockResolvedValue([]);
    vi.mocked(deleteWellnessGoal).mockResolvedValue(undefined);
    renderGoals();
    const user = userEvent.setup();
    await user.click(
      await screen.findByRole('button', {
        name: `Delete ${wellnessGoal.title}`,
      }),
    );
    await user.click(screen.getByRole('button', { name: 'Confirm delete' }));
    expect(
      await screen.findByText('Wellness goal deleted.'),
    ).toBeInTheDocument();
    expect(
      await screen.findByText('No wellness goals yet.'),
    ).toBeInTheDocument();
    expect(deleteWellnessGoal).toHaveBeenCalledWith(
      'access-token',
      wellnessGoal.goal_id,
    );
  });

  it('preserves the goal and confirmation after delete failure', async () => {
    vi.mocked(listWellnessGoals).mockResolvedValue([wellnessGoal]);
    vi.mocked(deleteWellnessGoal).mockRejectedValue(new Error('offline'));
    renderGoals();
    const user = userEvent.setup();
    await user.click(
      await screen.findByRole('button', {
        name: `Delete ${wellnessGoal.title}`,
      }),
    );
    await user.click(screen.getByRole('button', { name: 'Confirm delete' }));
    expect(await screen.findByText(/couldn't delete/i)).toBeInTheDocument();
    expect(goalCard()).toBeInTheDocument();
    expect(
      screen.getByRole('group', { name: `Delete ${wellnessGoal.title}` }),
    ).toBeInTheDocument();
  });
});
