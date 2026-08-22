import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, within } from '@testing-library/react';
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
  dailyNutritionRecord,
  hydrationRecord,
  mealRecord,
  menstrualBleedingRecord,
  menstrualCycleRecord,
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
              <Route path="goals" element={<h1>Goals page</h1>} />
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
  it('renders the empty state and exactly the ten implemented entry types', async () => {
    vi.mocked(listWellnessRecords).mockResolvedValue([]);
    renderRecords();

    expect(
      await screen.findByRole('heading', { name: 'No wellness records yet' }),
    ).toBeInTheDocument();
    const selector = screen.getByRole('group', { name: 'Record type' });
    expect(within(selector).getAllByRole('button')).toHaveLength(10);
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
    expect(
      within(selector).getByRole('button', { name: /^Meal/ }),
    ).toBeInTheDocument();
    expect(
      within(selector).getByRole('button', { name: /^Daily nutrition/ }),
    ).toBeInTheDocument();
    expect(
      within(selector).getByRole('button', { name: /^Menstrual bleeding/ }),
    ).toBeInTheDocument();
    expect(
      within(selector).getByRole('button', { name: /^Menstrual cycle/ }),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Import CSV' })).toHaveAttribute(
      'href',
      '/app/records/import',
    );
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
    await user.click(screen.getByRole('button', { name: /^Meal/ }));
    expect(screen.getByLabelText('Meal type')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /^Daily nutrition/ }));
    expect(screen.getByLabelText('Nutrition date')).toBeInTheDocument();
    await user.click(
      screen.getByRole('button', { name: /^Menstrual bleeding/ }),
    );
    expect(screen.getByLabelText('Flow description')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /^Menstrual cycle/ }));
    expect(screen.getByLabelText('Cycle start date')).toBeInTheDocument();
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
      resetValue: null,
    },
    {
      selector: /^Workout/,
      field: 'Distance (kilometers)',
      value: '4.2',
      save: 'Save workout record',
      success: 'Workout record saved.',
      type: 'workout',
      record: workoutRecord,
      resetValue: null,
    },
    {
      selector: /^Body measurement/,
      field: 'Weight (kilograms)',
      value: '72.4',
      save: 'Save body measurement',
      success: 'Body measurement record saved.',
      type: 'body_measurement',
      record: bodyMeasurementRecord,
      resetValue: null,
    },
    {
      selector: /^Meal/,
      field: 'Energy (kcal)',
      value: '420',
      selectField: 'Meal type',
      selectValue: 'lunch',
      save: 'Save meal record',
      success: 'Meal record saved.',
      type: 'meal',
      record: mealRecord,
      resetValue: null,
    },
    {
      selector: /^Daily nutrition/,
      field: 'Protein (grams)',
      value: '24',
      save: 'Save daily nutrition record',
      success: 'Daily nutrition record saved.',
      type: 'daily_nutrition',
      record: dailyNutritionRecord,
      resetValue: null,
    },
    {
      selector: /^Menstrual bleeding/,
      field: 'Notes (optional)',
      value: 'Observation note',
      selectField: 'Flow description',
      selectValue: 'light',
      save: 'Save bleeding observation',
      success: 'Menstrual bleeding observation record saved.',
      type: 'menstrual_bleeding',
      record: menstrualBleedingRecord,
      resetValue: '',
    },
    {
      selector: /^Menstrual cycle/,
      field: 'Notes (optional)',
      value: 'Synthetic cycle note',
      save: 'Save menstrual cycle',
      success: 'Menstrual cycle record saved.',
      type: 'menstrual_cycle',
      record: menstrualCycleRecord,
      resetValue: '',
    },
  ])(
    'saves and resets the $type form only after server success',
    async ({
      selector,
      field,
      value,
      selectField,
      selectValue,
      save,
      success,
      type,
      record,
      resetValue,
    }) => {
      vi.mocked(listWellnessRecords).mockResolvedValue([]);
      vi.mocked(createWellnessRecord).mockResolvedValue(record);
      renderRecords();
      const user = userEvent.setup();
      await screen.findByText('No wellness records yet');
      await user.click(screen.getByRole('button', { name: selector }));
      if (selectField && selectValue) {
        await user.selectOptions(
          screen.getByLabelText(selectField),
          selectValue,
        );
      }
      const input = screen.getByLabelText(field);
      if (input.getAttribute('type') === 'date') {
        fireEvent.change(input, { target: { value } });
      } else {
        await user.type(input, value);
      }
      await user.click(screen.getByRole('button', { name: save }));

      expect(await screen.findByText(success)).toBeInTheDocument();
      expect(createWellnessRecord).toHaveBeenCalledWith(
        'access-token',
        expect.objectContaining({ record_type: type }),
      );
      expect(screen.getByLabelText(field)).toHaveValue(resetValue);
    },
  );

  it('safely presents recent record types with exhaustive labels', async () => {
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

  it('provides real Home, Records, Goals, and Profile navigation without dead links', async () => {
    vi.mocked(listWellnessRecords).mockResolvedValue([]);
    renderRecords();
    await screen.findByText('No wellness records yet');

    const desktopNav = screen.getByRole('navigation', {
      name: 'Application navigation',
    });
    expect(within(desktopNav).getAllByRole('link')).toHaveLength(4);
    expect(
      within(desktopNav).getByRole('link', { name: 'Records' }),
    ).toHaveClass('active');
    expect(
      within(desktopNav).getByRole('link', { name: 'Goals' }),
    ).toHaveAttribute('href', '/app/goals');
  });
});
