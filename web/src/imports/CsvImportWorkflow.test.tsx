import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { ApiError } from '../api/client';
import {
  importWellnessCsv,
  type CsvImportRequest,
  type CsvImportResponse,
} from '../api/imports';
import { queryKeys } from '../api/queryKeys';
import { AuthContext } from '../auth/authContext';
import { createAuthValue, currentUser } from '../test/authTestUtils';
import { CsvImportWorkflow, MAX_CSV_IMPORT_BYTES } from './CsvImportWorkflow';

vi.mock('../api/imports', async (importOriginal) => {
  const original = await importOriginal<typeof import('../api/imports')>();
  return { ...original, importWellnessCsv: vi.fn() };
});

const csvContent = 'recorded_at,volume_value\n2026-08-20T10:00:00+05:30,500\n';

function report(overrides: Partial<CsvImportResponse> = {}): CsvImportResponse {
  return {
    schema_version: 1,
    record_type: 'hydration',
    mode: 'validate',
    total_rows: 3,
    valid_rows: 2,
    invalid_rows: 0,
    duplicate_rows: 1,
    ready_rows: 1,
    imported_rows: 0,
    can_commit: true,
    issues: [],
    duplicates: [{ row_number: 3, reason: 'existing_record' }],
    ...overrides,
  };
}

function csvFile(name = 'synthetic-hydration.csv', content = csvContent) {
  const file = new File([content], name, { type: 'text/csv' });
  Object.defineProperty(file, 'text', {
    configurable: true,
    value: vi.fn().mockResolvedValue(content),
  });
  return file;
}

function renderWorkflow() {
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
  render(
    <QueryClientProvider client={queryClient}>
      <AuthContext.Provider value={auth}>
        <CsvImportWorkflow />
      </AuthContext.Provider>
    </QueryClientProvider>,
  );
  return { queryClient, auth };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((next) => {
    resolve = next;
  });
  return { promise, resolve };
}

async function selectHydrationCsv(user: ReturnType<typeof userEvent.setup>) {
  await user.selectOptions(
    screen.getByLabelText('Record category'),
    'hydration',
  );
  await user.upload(screen.getByLabelText('CSV file'), csvFile());
  expect(
    await screen.findByText(/synthetic-hydration\.csv/),
  ).toBeInTheDocument();
}

describe('CsvImportWorkflow', () => {
  it('starts empty and offers exactly the six CSV v1 categories', () => {
    renderWorkflow();

    const category = screen.getByLabelText('Record category');
    expect(within(category).getAllByRole('option')).toHaveLength(6);
    expect(
      within(category).getByRole('option', { name: 'Sleep' }),
    ).toBeInTheDocument();
    expect(
      within(category).getByRole('option', { name: 'Wellness check-in' }),
    ).toBeInTheDocument();
    expect(
      within(category).queryByRole('option', { name: 'Workout' }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Validate CSV' })).toBeDisabled();
    expect(screen.queryByText('Validation report')).not.toBeInTheDocument();
  });

  it('validates exact transient content and presents issues and duplicates without raw rows', async () => {
    vi.mocked(importWellnessCsv).mockResolvedValue(
      report({
        invalid_rows: 1,
        ready_rows: 0,
        can_commit: false,
        issues: [
          {
            row_number: 2,
            field: 'volume_value',
            code: 'invalid_value',
            message: 'volume_value must be numeric',
          },
        ],
      }),
    );
    renderWorkflow();
    const user = userEvent.setup();
    await selectHydrationCsv(user);
    await user.click(screen.getByRole('button', { name: 'Validate CSV' }));

    expect(importWellnessCsv).toHaveBeenCalledWith('access-token', {
      schema_version: 1,
      record_type: 'hydration',
      mode: 'validate',
      content: csvContent,
    });
    expect(await screen.findByText('Validation report')).toBeInTheDocument();
    expect(screen.getByText('Row 2 · volume_value')).toBeInTheDocument();
    expect(
      screen.getByText('volume_value must be numeric'),
    ).toBeInTheDocument();
    expect(screen.getByText('Row 3')).toBeInTheDocument();
    expect(screen.getByText(/already in your history/)).toBeInTheDocument();
    expect(screen.queryByText(csvContent)).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Import ready rows' }),
    ).not.toBeInTheDocument();
  });

  it('clears stale validation after either category or file changes', async () => {
    vi.mocked(importWellnessCsv).mockResolvedValue(report());
    renderWorkflow();
    const user = userEvent.setup();
    await selectHydrationCsv(user);
    await user.click(screen.getByRole('button', { name: 'Validate CSV' }));
    expect(await screen.findByText('Validation report')).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText('Record category'), 'sleep');
    expect(screen.queryByText('Validation report')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Validate CSV' }));
    expect(await screen.findByText('Validation report')).toBeInTheDocument();
    await user.upload(
      screen.getByLabelText('CSV file'),
      csvFile('corrected.csv', `${csvContent}2026-08-21T10:00:00+05:30,250\n`),
    );
    expect(await screen.findByText(/corrected\.csv/)).toBeInTheDocument();
    expect(screen.queryByText('Validation report')).not.toBeInTheDocument();
  });

  it('commits only after validation and invalidates records and summary after server success', async () => {
    vi.mocked(importWellnessCsv).mockImplementation(
      async (_token, request: CsvImportRequest) =>
        request.mode === 'validate'
          ? report()
          : report({ mode: 'commit', imported_rows: 1 }),
    );
    const { queryClient } = renderWorkflow();
    queryClient.setQueryData(queryKeys.records, []);
    queryClient.setQueryData(queryKeys.summary, {});
    queryClient.setQueryData(queryKeys.goals, []);
    const user = userEvent.setup();
    await selectHydrationCsv(user);
    await user.click(screen.getByRole('button', { name: 'Validate CSV' }));
    await user.click(
      await screen.findByRole('button', { name: 'Import ready rows' }),
    );

    expect(importWellnessCsv).toHaveBeenLastCalledWith('access-token', {
      schema_version: 1,
      record_type: 'hydration',
      mode: 'commit',
      content: csvContent,
    });
    expect(
      await screen.findByText(/Import confirmed: 1 row imported/),
    ).toBeInTheDocument();
    expect(queryClient.getQueryState(queryKeys.records)?.isInvalidated).toBe(
      true,
    );
    expect(queryClient.getQueryState(queryKeys.summary)?.isInvalidated).toBe(
      true,
    );
    expect(queryClient.getQueryState(queryKeys.goals)?.isInvalidated).toBe(
      false,
    );
  });

  it('disables inputs during validation and commit without optimistically changing records', async () => {
    const validation = deferred<CsvImportResponse>();
    const commit = deferred<CsvImportResponse>();
    vi.mocked(importWellnessCsv)
      .mockReturnValueOnce(validation.promise)
      .mockReturnValueOnce(commit.promise);
    const { queryClient } = renderWorkflow();
    queryClient.setQueryData(queryKeys.records, ['server-owned-placeholder']);
    const user = userEvent.setup();
    await selectHydrationCsv(user);
    await user.click(screen.getByRole('button', { name: 'Validate CSV' }));

    expect(screen.getByText('Validating CSV…')).toBeInTheDocument();
    expect(screen.getByLabelText('Record category')).toBeDisabled();
    expect(screen.getByLabelText('CSV file')).toBeDisabled();
    await act(async () => {
      validation.resolve(report());
    });

    await user.click(
      await screen.findByRole('button', { name: 'Import ready rows' }),
    );
    expect(screen.getByText('Importing ready rows…')).toBeInTheDocument();
    expect(queryClient.getQueryData(queryKeys.records)).toEqual([
      'server-owned-placeholder',
    ]);
    await act(async () => {
      commit.resolve(report({ mode: 'commit', imported_rows: 1 }));
    });
    expect(await screen.findByText(/Import confirmed/)).toBeInTheDocument();
  });

  it('shows a changed commit-time validation report without claiming success', async () => {
    vi.mocked(importWellnessCsv)
      .mockResolvedValueOnce(report())
      .mockResolvedValueOnce(
        report({
          mode: 'commit',
          can_commit: false,
          invalid_rows: 1,
          ready_rows: 0,
          issues: [
            {
              row_number: 2,
              field: 'recorded_at',
              code: 'invalid_value',
              message: 'recorded_at must include a UTC offset',
            },
          ],
        }),
      );
    const { queryClient } = renderWorkflow();
    const user = userEvent.setup();
    await selectHydrationCsv(user);
    await user.click(screen.getByRole('button', { name: 'Validate CSV' }));
    await user.click(
      await screen.findByRole('button', { name: 'Import ready rows' }),
    );

    expect(
      await screen.findByText(/Server revalidation found issues/),
    ).toBeInTheDocument();
    expect(screen.getByText(/must include a UTC offset/)).toBeInTheDocument();
    expect(screen.queryByText(/Import confirmed/)).not.toBeInTheDocument();
    expect(queryClient.getQueryState(queryKeys.records)).toBeUndefined();
  });

  it('reports file read and size failures without contacting the server', async () => {
    renderWorkflow();
    const user = userEvent.setup();
    const unreadable = csvFile('unreadable.csv');
    Object.defineProperty(unreadable, 'text', {
      value: vi.fn().mockRejectedValue(new Error('Synthetic read failure')),
    });
    await user.upload(screen.getByLabelText('CSV file'), unreadable);
    expect(await screen.findByText(/could not be read/)).toBeInTheDocument();

    const oversized = csvFile('oversized.csv');
    Object.defineProperty(oversized, 'size', {
      value: MAX_CSV_IMPORT_BYTES + 1,
    });
    await user.upload(screen.getByLabelText('CSV file'), oversized);
    expect(await screen.findByText(/no larger than 1 MB/)).toBeInTheDocument();

    await user.upload(
      screen.getByLabelText('CSV file'),
      csvFile('empty.csv', ''),
    );
    expect(
      await screen.findByText(/contains a header and data/),
    ).toBeInTheDocument();
    expect(importWellnessCsv).not.toHaveBeenCalled();
  });

  it.each([
    ['validate', 'validate this CSV'],
    ['commit', 'did not confirm this import'],
  ] as const)(
    'shows safe %s failures without claiming an import',
    async (stage, message) => {
      const failure = new ApiError('Sensitive server detail', {
        kind: 'api',
        status: 400,
        code: 'application_validation_error',
      });
      if (stage === 'validate') {
        vi.mocked(importWellnessCsv).mockRejectedValueOnce(failure);
      } else {
        vi.mocked(importWellnessCsv)
          .mockResolvedValueOnce(report())
          .mockRejectedValueOnce(failure);
      }
      renderWorkflow();
      const user = userEvent.setup();
      await selectHydrationCsv(user);
      await user.click(screen.getByRole('button', { name: 'Validate CSV' }));
      if (stage === 'commit') {
        await user.click(
          await screen.findByRole('button', { name: 'Import ready rows' }),
        );
      }

      expect(
        await screen.findByText(new RegExp(message, 'i')),
      ).toBeInTheDocument();
      expect(
        screen.queryByText('Sensitive server detail'),
      ).not.toBeInTheDocument();
      expect(screen.queryByText(/Import confirmed/)).not.toBeInTheDocument();
    },
  );
});
