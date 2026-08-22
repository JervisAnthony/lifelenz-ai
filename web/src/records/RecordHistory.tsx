import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { ApiError } from '../api/client';
import {
  deleteWellnessRecord,
  updateWellnessRecord,
} from '../api/records';
import { queryKeys } from '../api/queryKeys';
import type {
  WellnessRecord,
  WellnessRecordCreateRequest,
} from '../api/types';
import { useAuth } from '../auth/authContext';
import { Alert } from '../components/Alert';
import { prepareCorrectionRequest } from './recordEditing';
import { recordEntryDefinition } from './recordEntryRegistry';
import { presentRecord } from './recordPresentation';
import { recordTypeLabels } from './recordTypes';
import './RecordHistory.css';

function correctionErrorMessage(error: unknown, action: 'update' | 'delete') {
  if (error instanceof ApiError) {
    if (error.kind === 'network') {
      return "We couldn't reach LifeLenz. Nothing has been changed.";
    }
    if (error.code === 'wellness_record_not_found') {
      return 'This record is no longer available. Refresh the history and try again.';
    }
    if (
      error.code === 'request_validation_error' ||
      error.code === 'domain_validation_error' ||
      error.code === 'application_validation_error'
    ) {
      return action === 'update'
        ? "We couldn't save this correction. Review the details and try again."
        : "We couldn't delete this record. Please try again.";
    }
  }
  return action === 'update'
    ? "We couldn't save this correction. Please try again."
    : "We couldn't delete this record. Please try again.";
}

export function RecordHistory({ records }: { records: WellnessRecord[] }) {
  const { accessToken, handleSessionError, refreshCurrentUser } = useAuth();
  const queryClient = useQueryClient();
  const [editingRecordId, setEditingRecordId] = useState<string | null>(null);
  const [deletingRecordId, setDeletingRecordId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const updateMutation = useMutation({
    mutationFn: async ({
      record,
      request,
    }: {
      record: WellnessRecord;
      request: WellnessRecordCreateRequest;
    }) => {
      if (!accessToken) {
        throw new Error('Authenticated access token is unavailable');
      }
      return updateWellnessRecord(
        accessToken,
        record.metadata.record_id,
        prepareCorrectionRequest(record, request),
      );
    },
    retry: false,
    onSuccess: async (updated) => {
      setActionError(null);
      setActionSuccess(
        `${recordTypeLabels[updated.record_type]} record corrected.`,
      );
      setEditingRecordId(null);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.records }),
        queryClient.invalidateQueries({ queryKey: queryKeys.summary }),
      ]);
    },
    onError: async (caughtError) => {
      if (
        caughtError instanceof ApiError &&
        caughtError.code === 'profile_not_configured'
      ) {
        void refreshCurrentUser();
      }
      if (!handleSessionError(caughtError)) {
        setActionSuccess(null);
        setActionError(correctionErrorMessage(caughtError, 'update'));
      }
      if (
        caughtError instanceof ApiError &&
        caughtError.code === 'wellness_record_not_found'
      ) {
        await queryClient.invalidateQueries({ queryKey: queryKeys.records });
      }
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (record: WellnessRecord) => {
      if (!accessToken) {
        throw new Error('Authenticated access token is unavailable');
      }
      await deleteWellnessRecord(accessToken, record.metadata.record_id);
      return record;
    },
    retry: false,
    onSuccess: async (record) => {
      setActionError(null);
      setActionSuccess(
        `${recordTypeLabels[record.record_type]} record deleted.`,
      );
      setDeletingRecordId(null);
      if (editingRecordId === record.metadata.record_id) {
        setEditingRecordId(null);
      }
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.records }),
        queryClient.invalidateQueries({ queryKey: queryKeys.summary }),
      ]);
    },
    onError: async (caughtError) => {
      if (
        caughtError instanceof ApiError &&
        caughtError.code === 'profile_not_configured'
      ) {
        void refreshCurrentUser();
      }
      if (!handleSessionError(caughtError)) {
        setActionSuccess(null);
        setActionError(correctionErrorMessage(caughtError, 'delete'));
      }
      if (
        caughtError instanceof ApiError &&
        caughtError.code === 'wellness_record_not_found'
      ) {
        await queryClient.invalidateQueries({ queryKey: queryKeys.records });
      }
    },
  });

  if (!records.length) {
    return (
      <div className="records-empty">
        <h3>No records match these filters</h3>
        <p>
          Adjust the record type or date range to review another part of your
          history.
        </p>
      </div>
    );
  }

  const newestFirst = [...records].reverse();
  return (
    <>
      {actionError ? <Alert>{actionError}</Alert> : null}
      {actionSuccess ? <Alert tone="success">{actionSuccess}</Alert> : null}
      <p className="summary-source" role="status">
        {records.length.toLocaleString()}{' '}
        {records.length === 1 ? 'record' : 'records'} found
      </p>
      <ol
        className="recent-records record-history"
        aria-label="Filtered wellness record history"
      >
        {newestFirst.map((record) => {
          const presentation = presentRecord(record);
          const definition = recordEntryDefinition(record.record_type);
          const isEditing = editingRecordId === record.metadata.record_id;
          const isDeleting = deletingRecordId === record.metadata.record_id;
          const busy = updateMutation.isPending || deleteMutation.isPending;
          const EditForm = definition?.Form;
          return (
            <li key={record.metadata.record_id} className="record-history__item">
              <div className="record-history__summary">
                <div>
                  <h3>{presentation.label}</h3>
                  <p>{presentation.summary}</p>
                </div>
                <time dateTime={record.metadata.recorded_at}>
                  {presentation.timestamp}
                </time>
              </div>

              <div className="record-history__actions">
                <button
                  type="button"
                  className="button button--secondary"
                  aria-expanded={isEditing}
                  disabled={busy}
                  onClick={() => {
                    setActionError(null);
                    setActionSuccess(null);
                    setDeletingRecordId(null);
                    setEditingRecordId(
                      isEditing ? null : record.metadata.record_id,
                    );
                  }}
                >
                  {isEditing ? 'Cancel correction' : 'Correct record'}
                </button>
                <button
                  type="button"
                  className="button button--secondary"
                  aria-expanded={isDeleting}
                  disabled={busy}
                  onClick={() => {
                    setActionError(null);
                    setActionSuccess(null);
                    setEditingRecordId(null);
                    setDeletingRecordId(
                      isDeleting ? null : record.metadata.record_id,
                    );
                  }}
                >
                  {isDeleting ? 'Cancel delete' : 'Delete record'}
                </button>
              </div>

              {isEditing && EditForm ? (
                <section
                  className="record-form-card record-history__correction"
                  aria-label={`Correct ${presentation.label.toLowerCase()} record`}
                >
                  <div className="record-form-card__heading">
                    <h4>Correct this record</h4>
                    <p>
                      Update the recorded details. The record identity, type,
                      ownership, and original data source stay unchanged.
                    </p>
                  </div>
                  <EditForm
                    key={record.metadata.record_id}
                    initialRecord={record}
                    isSaving={updateMutation.isPending}
                    onSubmit={async (request) => {
                      await updateMutation.mutateAsync({ record, request });
                    }}
                  />
                </section>
              ) : null}

              {isDeleting ? (
                <div
                  className="record-history__confirmation"
                  role="group"
                  aria-label={`Delete ${presentation.label.toLowerCase()} record`}
                >
                  <p>
                    Delete this {presentation.label.toLowerCase()} record? This
                    permanently removes this entry from LifeLenz history and may
                    change summaries calculated from your records.
                  </p>
                  <div>
                    <button
                      type="button"
                      className="button button--secondary"
                      disabled={deleteMutation.isPending}
                      onClick={() => setDeletingRecordId(null)}
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      className="button button--primary"
                      disabled={deleteMutation.isPending}
                      onClick={() => deleteMutation.mutate(record)}
                    >
                      {deleteMutation.isPending ? 'Deleting…' : 'Delete record'}
                    </button>
                  </div>
                </div>
              ) : null}
            </li>
          );
        })}
      </ol>
    </>
  );
}
