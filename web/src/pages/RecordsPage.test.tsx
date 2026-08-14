import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import { ApiError } from '../api/client';
import { createWellnessRecord, listWellnessRecords } from '../api/records';
import { queryKeys } from '../api/queryKeys';
import { AuthContext } from '../auth/authContext';
import { AppShell } from '../components/AppShell';
import { recordTypeLabels } from '../records/recordTypes';
import { createAuthValue, currentUser } from '../test/authTestUtils';
import {
  bodyMeasurementRecord,
  dailyActivityRecord,
  hydrationRecord,
  wellnessProfile,
  wellnessSummary,
  workoutRecord,
} from '../test/resourceFixtures';
import { RecordsPage } from './RecordsPage';

vi.mock('../api/records', () => ({
  createWellnessRecord: vi.fn(),
  listWellnessRecords: vi.fn(),
}));

function renderRecords() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  queryClient.setQueryData(queryKeys.summary, wellnessSummary);
  const auth = createAuthValue({
    status: 'authenticated',
    user: { ...currentUser, profile_ids: [wellnessProfile.profile_id] },
    accessToken: 'access-token',
  });
  render(
    <QueryClientProvider client={queryClient}>
      <AuthContext.Provider value={auth}>
        <MemoryRouter initialEntries={['/app/records']}>
          <Routes>
            <Route path="/app" element={<AppShell />}>
              <Route index element={<h1>Home page</h1>} />
              <Route path="records" element={<RecordsPage />} />
              <Route path="profile" element={<h1>Profile page</h1>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>
    </QueryClientProvider>,
  );
  return { queryClient };
}

describe('RecordsPage', () => {
  it('renders the empty state and exactly the six implemented entry types', async () => {
    vi.mocked(listWellnessRecords).mockResolvedValue([]);
    renderRecords();

    expect(
      await screen.findByRole('heading', { name: 'No wellness records yet' }),
    ).toBeInTheDocument();
    const selector = screen.getByRole('group', { name: 'Record type' });
    expect(within(selector).getAllByRole('button')).toHaveLength(6);
    expect(
      within(selector).getByRole('button', { name: /^Sleep/ }),
    ).toHaveAttribute('aria-pressed', 'true');
    expect(
      within(selector).getByRole('button', { name: /^Hydration/ }),
    ).toBeInTheDocument();
    expect(
      within(selector).getByRole('button', { name: /^Wellness check-in/ }),
    ).toBeInTheDocument();
    expect(
      within(selector).getByRole('button', { name: /^Daily activity/ }),
    ).toBeInTheDocument();
    expect(
      within(selector).getByRole('button', { name: /^Workout/ }),
    ).toBeInTheDocument();
    expect(
      within(selector).getByRole('button', { name: /^Body measurement/ }),
    ).toBeInTheDocument();
    expect(within(selector).queryByText('Meal')).not.toBeInTheDocument();
  });

  it('switches among each implemented form', async () => {
    vi.mocked(listWellnessRecords).mockResolvedValue([]);
    renderRecords();
    const user = userEvent.setup();
    await screen.findByText('No wellness records yet');

    expect(screen.getByLabelText('Sleep start')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /^Hydration/ }));
    expect(screen.getByLabelText('Volume (milliliters)')).toBeInTheDocument();
    await user.click(
      screen.getByRole('button', { name: /^Wellness check-in/ }),
    );
    expect(screen.getByLabelText('Mood score')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /^Daily activity/ }));
    expect(screen.getByLabelText('Activity date')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /^Workout/ }));
    expect(screen.getByLabelText('Workout type')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /^Body measurement/ }));
    expect(screen.getByLabelText('Weight (kilograms)')).toBeInTheDocument();
  });

  it('creates a record, refreshes the recent list and summary, then resets the form', async () => {
    vi.mocked(listWellnessRecords)
      .mockResolvedValueOnce([])
      .mockResolvedValue([hydrationRecord]);
    vi.mocked(createWellnessRecord).mockResolvedValue(hydrationRecord);
    const { queryClient } = renderRecords();
    const user = userEvent.setup();
    await screen.findByText('No wellness records yet');
    await user.click(screen.getByRole('button', { name: /^Hydration/ }));
    await user.type(screen.getByLabelText('Volume (milliliters)'), '350');
    await user.click(
      screen.getByRole('button', { name: 'Save hydration record' }),
    );

    expect(
      await screen.findByText('Hydration record saved.'),
    ).toBeInTheDocument();
    expect(createWellnessRecord).toHaveBeenCalledWith(
      'access-token',
      expect.objectContaining({ record_type: 'hydration' }),
    );
    expect(await screen.findByText('350 mL · Water')).toBeInTheDocument();
    expect(screen.getByLabelText('Volume (milliliters)')).toHaveValue(null);
    expect(queryClient.getQueryState(queryKeys.summary)?.isInvalidated).toBe(
      true,
    );
  });

  it('shows a safe create error and preserves the entered data', async () => {
    vi.mocked(listWellnessRecords).mockResolvedValue([]);
    vi.mocked(createWellnessRecord).mockRejectedValue(
      new ApiError('internal validation detail', {
        kind: 'api',
        status: 422,
        code: 'domain_validation_error',
      }),
    );
    renderRecords();
    const user = userEvent.setup();
    await screen.findByText('No wellness records yet');
    await user.click(screen.getByRole('button', { name: /^Hydration/ }));
    await user.type(screen.getByLabelText('Volume (milliliters)'), '275');
    await user.click(
      screen.getByRole('button', { name: 'Save hydration record' }),
    );

    expect(
      await screen.findByText(/review the details and try again/i),
    ).toBeInTheDocument();
    expect(createWellnessRecord).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText('Volume (milliliters)')).toHaveValue(275);
    expect(
      screen.queryByText('internal validation detail'),
    ).not.toBeInTheDocument();
  });

  it.each([
    {
      selector: /^Daily activity/,
      field: 'Steps',
      value: '5100',
      save: 'Save daily activity record',
      success: 'Daily activity record saved.',
      type: 'daily_activity',
      record: dailyActivityRecord,
    },
    {
      selector: /^Workout/,
      field: 'Distance (kilometers)',
      value: '4.2',
      save: 'Save workout record',
      success: 'Workout record saved.',
      type: 'workout',
      record: workoutRecord,
    },
    {
      selector: /^Body measurement/,
      field: 'Weight (kilograms)',
      value: '72.4',
      save: 'Save body measurement',
      success: 'Body measurement record saved.',
      type: 'body_measurement',
      record: bodyMeasurementRecord,
    },
  ])(
    'saves and resets the $type form only after server success',
    async ({ selector, field, value, save, success, type, record }) => {
      vi.mocked(listWellnessRecords).mockResolvedValue([]);
      vi.mocked(createWellnessRecord).mockResolvedValue(record);
      renderRecords();
      const user = userEvent.setup();
      await screen.findByText('No wellness records yet');
      await user.click(screen.getByRole('button', { name: selector }));
      await user.type(screen.getByLabelText(field), value);
      await user.click(screen.getByRole('button', { name: save }));

      expect(await screen.findByText(success)).toBeInTheDocument();
      expect(createWellnessRecord).toHaveBeenCalledWith(
        'access-token',
        expect.objectContaining({ record_type: type }),
      );
      expect(screen.getByLabelText(field)).toHaveValue(null);
    },
  );

  it('safely presents unsupported-create record types with exhaustive labels', async () => {
    vi.mocked(listWellnessRecords).mockResolvedValue([
      dailyActivityRecord,
      hydrationRecord,
    ]);
    renderRecords();

    const recentRecords = screen.getByRole('region', {
      name: 'Recent records',
    });
    expect(
      await within(recentRecords).findByText('Daily activity'),
    ).toBeInTheDocument();
    expect(screen.queryByText('daily_activity')).not.toBeInTheDocument();
    expect(Object.keys(recordTypeLabels)).toHaveLength(10);
    expect(
      within(recentRecords).getByText('350 mL · Water'),
    ).toBeInTheDocument();
  });

  it('keeps entry available and offers retry when the recent list fails', async () => {
    vi.mocked(listWellnessRecords).mockRejectedValue(new Error('offline'));
    renderRecords();

    expect(
      await screen.findByRole('button', { name: 'Try records again' }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText('Sleep start')).toBeInTheDocument();
  });

  it('provides real Home, Records, and Profile navigation without dead links', async () => {
    vi.mocked(listWellnessRecords).mockResolvedValue([]);
    renderRecords();
    await screen.findByText('No wellness records yet');

    const desktopNav = screen.getByRole('navigation', {
      name: 'Application navigation',
    });
    expect(within(desktopNav).getAllByRole('link')).toHaveLength(3);
    expect(
      within(desktopNav).getByRole('link', { name: 'Records' }),
    ).toHaveClass('active');
  });
});
