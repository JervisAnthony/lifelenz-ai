import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { ApiError } from '../api/client';
import { createWellnessRecord, listWellnessRecords } from '../api/records';
import { queryKeys } from '../api/queryKeys';
import type { WellnessRecordCreateRequest } from '../api/types';
import { useAuth } from '../auth/authContext';
import { Alert } from '../components/Alert';
import { RecentRecords } from '../records/RecentRecords';
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
    </div>
  );
}
