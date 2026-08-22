import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { ApiError } from '../api/client';
import {
  createWellnessRecord,
  listWellnessRecords,
  type WellnessRecordListFilters,
} from '../api/records';
import { queryKeys } from '../api/queryKeys';
import type {
  WellnessRecordCreateRequest,
  WellnessRecordType,
} from '../api/types';
import { useAuth } from '../auth/authContext';
import { Alert } from '../components/Alert';
import { buildRecordHistoryFilters } from '../records/historyFilters';
import { RecentRecords } from '../records/RecentRecords';
import { RecordHistory } from '../records/RecordHistory';
import {
  recordEntryDefinition,
  recordEntryRegistry,
} from '../records/recordEntryRegistry';
import { recordTypeLabels, type RecordEntryType } from '../records/recordTypes';

function recordErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.kind === 'network') {
      return "We couldn't reach LifeLenz. Your entries are still in the form.";
    }
    if (
      error.code === 'request_validation_error' ||
      error.code === 'domain_validation_error' ||
      error.code === 'application_validation_error'
    ) {
      return "We couldn't save this wellness record. Please review the details and try again.";
    }
  }
  return "We couldn't save this wellness record. Please try again.";
}

export function RecordsPage() {
  const { accessToken, handleSessionError, refreshCurrentUser } = useAuth();
  const queryClient = useQueryClient();
  const [selectedType, setSelectedType] = useState<RecordEntryType>('sleep');
  const [formVersion, setFormVersion] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyRecordType, setHistoryRecordType] = useState<
    WellnessRecordType | 'all'
  >('all');
  const [historyStartDate, setHistoryStartDate] = useState('');
  const [historyEndDate, setHistoryEndDate] = useState('');
  const [historyFilterError, setHistoryFilterError] = useState<string | null>(null);
  const [appliedHistoryFilters, setAppliedHistoryFilters] =
    useState<WellnessRecordListFilters>({});

  const recordsQuery = useQuery({
    queryKey: queryKeys.records,
    queryFn: async ({ signal }) => {
      try {
        return await listWellnessRecords(accessToken as string, signal);
      } catch (caughtError) {
        handleSessionError(caughtError);
        if (
          caughtError instanceof ApiError &&
          caughtError.code === 'profile_not_configured'
        ) {
          void refreshCurrentUser();
        }
        throw caughtError;
      }
    },
    enabled: Boolean(accessToken),
    retry: false,
  });

  const historyQuery = useQuery({
    queryKey: queryKeys.recordHistory(
      appliedHistoryFilters.recordType ?? null,
      appliedHistoryFilters.start ?? null,
      appliedHistoryFilters.end ?? null,
    ),
    queryFn: async ({ signal }) => {
      try {
        return await listWellnessRecords(
          accessToken as string,
          signal,
          appliedHistoryFilters,
        );
      } catch (caughtError) {
        handleSessionError(caughtError);
        if (
          caughtError instanceof ApiError &&
          caughtError.code === 'profile_not_configured'
        ) {
          void refreshCurrentUser();
        }
        throw caughtError;
      }
    },
    enabled: Boolean(accessToken && historyOpen),
    retry: false,
  });

  const createMutation = useMutation({
    mutationFn: (request: WellnessRecordCreateRequest) => {
      if (!accessToken) {
        throw new Error('Authenticated access token is unavailable');
      }
      return createWellnessRecord(accessToken, request);
    },
    retry: false,
    onSuccess: async (record) => {
      setError(null);
      setSuccess(`${recordTypeLabels[record.record_type]} record saved.`);
      setFormVersion((version) => version + 1);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.records }),
        queryClient.invalidateQueries({ queryKey: queryKeys.summary }),
      ]);
    },
    onError: (caughtError) => {
      if (
        caughtError instanceof ApiError &&
        caughtError.code === 'profile_not_configured'
      ) {
        void refreshCurrentUser();
      }
      if (!handleSessionError(caughtError)) {
        setSuccess(null);
        setError(recordErrorMessage(caughtError));
      }
    },
  });

  useEffect(() => {
    document.title = 'Records | LifeLenz';
  }, []);

  const definition = recordEntryDefinition(selectedType);
  if (!definition) {
    return null;
  }
  const ActiveForm = definition.Form;

  return (
    <div className="records-page">
      <header className="page-intro">
        <p className="eyebrow">Your observations</p>
        <h1>Wellness records</h1>
        <p>
          Add structured everyday information without scores, targets, or
          medical interpretation.
        </p>
      </header>

      <section className="record-entry" aria-labelledby="add-record-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Record entry</p>
            <h2 id="add-record-heading">Add a wellness record</h2>
          </div>
          <p>Choose one of the record types currently available on the web.</p>
        </div>
        <div
          className="record-type-selector"
          role="group"
          aria-label="Record type"
        >
          {recordEntryRegistry.map((entry) => (
            <button
              key={entry.type}
              type="button"
              className={entry.type === selectedType ? 'is-selected' : ''}
              aria-pressed={entry.type === selectedType}
              onClick={() => {
                setSelectedType(entry.type);
                setError(null);
                setSuccess(null);
              }}
            >
              <strong>{entry.label}</strong>
              <span>{entry.description}</span>
            </button>
          ))}
        </div>
        <div className="record-form-card">
          <div className="record-form-card__heading">
            <h3>{definition.label}</h3>
            <p>{definition.description}</p>
          </div>
          {error ? <Alert>{error}</Alert> : null}
          {success ? <Alert tone="success">{success}</Alert> : null}
          <ActiveForm
            key={`${selectedType}-${formVersion}`}
            isSaving={createMutation.isPending}
            onSubmit={async (request) => {
              await createMutation.mutateAsync(request);
            }}
          />
        </div>
      </section>

      <section
        className="records-list-section"
        aria-labelledby="recent-records-heading"
      >
        <div className="section-heading">
          <div>
            <p className="eyebrow">Latest entries</p>
            <h2 id="recent-records-heading">Recent records</h2>
          </div>
          <p>Showing up to ten newest records from the server-owned history.</p>
        </div>
        {recordsQuery.isPending ? (
          <p className="inline-status" role="status">
            Loading recent records…
          </p>
        ) : recordsQuery.isError ? (
          <div className="summary-error">
            <Alert>We could not load your recent wellness records.</Alert>
            <button
              className="button button--secondary"
              onClick={() => void recordsQuery.refetch()}
            >
              Try records again
            </button>
          </div>
        ) : (
          <RecentRecords records={recordsQuery.data} />
        )}
      </section>

      <section
        className="records-list-section"
        aria-labelledby="record-history-heading"
      >
        <div className="section-heading">
          <div>
            <p className="eyebrow">Longitudinal review</p>
            <h2 id="record-history-heading">Record history</h2>
          </div>
          <button
            type="button"
            className="button button--secondary"
            aria-expanded={historyOpen}
            onClick={() => setHistoryOpen((open) => !open)}
          >
            {historyOpen ? 'Hide history' : 'Browse full history'}
          </button>
        </div>

        {historyOpen ? (
          <>
            <form
              className="record-form record-form-card"
              aria-label="Record history filters"
              onSubmit={(event) => {
                event.preventDefault();
                try {
                  const filters = buildRecordHistoryFilters({
                    recordType: historyRecordType,
                    startDate: historyStartDate,
                    endDate: historyEndDate,
                  });
                  setHistoryFilterError(null);
                  setAppliedHistoryFilters(filters);
                } catch (caughtError) {
                  setHistoryFilterError(
                    caughtError instanceof Error
                      ? caughtError.message
                      : 'Review the history filters and try again.',
                  );
                }
              }}
            >
              <div className="record-form-card__heading">
                <h3>Filter your history</h3>
                <p>
                  Filter by record type and, optionally, a complete local date
                  range. The backend remains the source of the returned history.
                </p>
              </div>
              {historyFilterError ? <Alert>{historyFilterError}</Alert> : null}
              <div className="record-form__grid">
                <label className="field">
                  <span>History record type</span>
                  <select
                    value={historyRecordType}
                    onChange={(event) =>
                      setHistoryRecordType(
                        event.target.value as WellnessRecordType | 'all',
                      )
                    }
                  >
                    <option value="all">All record types</option>
                    {recordEntryRegistry.map((entry) => (
                      <option key={entry.type} value={entry.type}>
                        {entry.label}
                      </option>
                    ))}
                  </select>
                </label>
                <div />
                <label className="field">
                  <span>History start date (optional)</span>
                  <input
                    type="date"
                    value={historyStartDate}
                    onChange={(event) => setHistoryStartDate(event.target.value)}
                  />
                </label>
                <label className="field">
                  <span>History end date (optional)</span>
                  <input
                    type="date"
                    min={historyStartDate || undefined}
                    value={historyEndDate}
                    onChange={(event) => setHistoryEndDate(event.target.value)}
                  />
                </label>
              </div>
              <div className="record-form__actions">
                <p>
                  Date filters include both selected calendar days in your local
                  time zone.
                </p>
                <div>
                  <button type="submit" className="button button--primary">
                    Apply filters
                  </button>
                  <button
                    type="button"
                    className="button button--secondary"
                    onClick={() => {
                      setHistoryRecordType('all');
                      setHistoryStartDate('');
                      setHistoryEndDate('');
                      setHistoryFilterError(null);
                      setAppliedHistoryFilters({});
                    }}
                  >
                    Clear filters
                  </button>
                </div>
              </div>
            </form>

            {historyQuery.isPending ? (
              <p className="inline-status" role="status">
                Loading record history…
              </p>
            ) : historyQuery.isError ? (
              <div className="summary-error">
                <Alert>We could not load your wellness record history.</Alert>
                <button
                  className="button button--secondary"
                  onClick={() => void historyQuery.refetch()}
                >
                  Try history again
                </button>
              </div>
            ) : (
              <RecordHistory records={historyQuery.data} />
            )}
          </>
        ) : (
          <p className="inline-status">
            Open the history browser to review all server-returned records or
            narrow them by type and date range.
          </p>
        )}
      </section>
    </div>
  );
}
