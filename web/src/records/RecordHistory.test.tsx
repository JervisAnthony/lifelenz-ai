import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { deleteWellnessRecord, updateWellnessRecord } from '../api/records';
import type { WellnessRecord } from '../api/types';
import { AuthContext } from '../auth/authContext';
import { createAuthValue, currentUser } from '../test/authTestUtils';
import { RecordHistory } from './RecordHistory';

vi.mock('../api/records', () => ({
  deleteWellnessRecord: vi.fn(),
  updateWellnessRecord: vi.fn(),
}));

function hydrationRecord(
  index: number,
): Extract<WellnessRecord, { record_type: 'hydration' }> {
  return {
    record_type: 'hydration',
    metadata: {
      record_id: `history-${index}`,
      recorded_at: `2026-08-${String(index + 10).padStart(2, '0')}T10:00:00+05:30`,
      source: 'manual',
      notes: null,
    },
    data: {
      volume_milliliters: 250 + index,
      beverage_type: 'water',
      caffeine_milligrams: null,
    },
  };
}

function renderHistory(records: WellnessRecord[]) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  const auth = createAuthValue({
    status: 'authenticated',
    user: { ...currentUser, profile_ids: ['synthetic-profile'] },
    accessToken: 'access-token',
  });
  const tree = (nextRecords: WellnessRecord[]) => (
    <QueryClientProvider client={queryClient}>
      <AuthContext.Provider value={auth}>
        <RecordHistory records={nextRecords} />
      </AuthContext.Provider>
    </QueryClientProvider>
  );
  const view = render(tree(records));
  return {
    queryClient,
    rerenderHistory(nextRecords: WellnessRecord[]) {
      view.rerender(tree(nextRecords));
    },
  };
}

describe('RecordHistory', () => {
  it('shows every returned record newest first', () => {
    renderHistory([hydrationRecord(0), hydrationRecord(1), hydrationRecord(2)]);

    expect(screen.getByRole('status')).toHaveTextContent('3 records found');
    const items = screen.getAllByRole('listitem');
    expect(items).toHaveLength(3);
    expect(within(items[0]).getByText(/^252 mL/)).toBeInTheDocument();
    expect(within(items[2]).getByText(/^250 mL/)).toBeInTheDocument();
  });

  it('renders an honest filtered empty state', () => {
    renderHistory([]);
    expect(
      screen.getByRole('heading', { name: 'No records match these filters' }),
    ).toBeInTheDocument();
  });

  it('keeps menstrual details restrained in full history', () => {
    const record: WellnessRecord = {
      record_type: 'menstrual_bleeding',
      metadata: {
        record_id: 'synthetic-menstrual-history',
        recorded_at: '2026-08-14T08:00:00+05:30',
        source: 'manual',
        notes: 'synthetic private note',
      },
      data: { flow: 'heavy', symptoms: [] },
    };

    renderHistory([record]);
    expect(
      screen.getByText('Menstrual bleeding observation'),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/heavy|synthetic private note/i),
    ).not.toBeInTheDocument();
  });

  it('prefills a correction form and sends the replacement through the server', async () => {
    const original = {
      ...hydrationRecord(0),
      metadata: {
        ...hydrationRecord(0).metadata,
        source: 'csv_import' as const,
      },
    };
    vi.mocked(updateWellnessRecord).mockImplementation(
      async (_token, _recordId, request) => {
        if (request.record_type !== 'hydration') {
          throw new Error('unexpected correction type');
        }
        return {
          ...original,
          metadata: {
            ...original.metadata,
            recorded_at: request.metadata.recorded_at,
            notes: request.metadata.notes,
          },
          data: request.data,
        };
      },
    );
    renderHistory([original]);
    const user = userEvent.setup();

    await user.click(screen.getByRole('button', { name: 'Correct record' }));
    expect(screen.getByLabelText('Volume (milliliters)')).toHaveValue(250);
    await user.clear(screen.getByLabelText('Volume (milliliters)'));
    await user.type(screen.getByLabelText('Volume (milliliters)'), '475');
    await user.click(
      screen.getByRole('button', { name: 'Save hydration record' }),
    );

    expect(updateWellnessRecord).toHaveBeenCalledWith(
      'access-token',
      'history-0',
      expect.objectContaining({
        record_type: 'hydration',
        metadata: expect.objectContaining({ source: 'csv_import' }),
        data: expect.objectContaining({ volume_milliliters: 475 }),
      }),
    );
    expect(
      await screen.findByText('Hydration record corrected.'),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('region', { name: 'Correct hydration record' }),
    ).not.toBeInTheDocument();
  });

  it('requires confirmation before deletion and removes nothing on cancel', async () => {
    renderHistory([hydrationRecord(0)]);
    const user = userEvent.setup();

    await user.click(screen.getByRole('button', { name: 'Delete record' }));
    expect(
      screen.getByRole('group', { name: 'Delete hydration record' }),
    ).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(deleteWellnessRecord).not.toHaveBeenCalled();
    expect(
      screen.queryByRole('group', { name: 'Delete hydration record' }),
    ).not.toBeInTheDocument();
  });

  it('keeps deletion feedback visible when the last history record disappears', async () => {
    vi.mocked(deleteWellnessRecord).mockResolvedValue(undefined);
    const { rerenderHistory } = renderHistory([hydrationRecord(0)]);
    const user = userEvent.setup();

    await user.click(screen.getByRole('button', { name: 'Delete record' }));
    const confirmation = screen.getByRole('group', {
      name: 'Delete hydration record',
    });
    await user.click(
      within(confirmation).getByRole('button', { name: 'Delete record' }),
    );

    expect(deleteWellnessRecord).toHaveBeenCalledWith(
      'access-token',
      'history-0',
    );
    expect(
      await screen.findByText('Hydration record deleted.'),
    ).toBeInTheDocument();

    rerenderHistory([]);

    expect(screen.getByText('Hydration record deleted.')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'No records match these filters' }),
    ).toBeInTheDocument();
  });
});
