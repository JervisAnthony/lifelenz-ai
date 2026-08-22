import { useRef, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { ApiError } from '../api/client';
import {
  csvImportRecordTypeLabels,
  csvImportRecordTypes,
  importWellnessCsv,
  type CsvImportRecordType,
  type CsvImportRequest,
  type CsvImportResponse,
} from '../api/imports';
import { queryKeys } from '../api/queryKeys';
import { useAuth } from '../auth/authContext';
import { Alert } from '../components/Alert';

export const MAX_CSV_IMPORT_BYTES = 1_000_000;

interface SelectedCsv {
  fileName: string;
  content: string;
  utf8Bytes: number;
}

interface ValidatedCsv {
  request: CsvImportRequest;
  report: CsvImportResponse;
}

function importErrorMessage(error: unknown, action: 'validate' | 'commit') {
  if (error instanceof ApiError && error.kind === 'network') {
    return action === 'validate'
      ? "We couldn't reach LifeLenz to validate this CSV. Please try again."
      : "We couldn't confirm whether the import completed. Review your records, then validate again before retrying.";
  }
  return action === 'validate'
    ? 'LifeLenz could not validate this CSV. Review the selection and try again.'
    : 'LifeLenz did not confirm this import. No local record list was changed.';
}

function duplicateDescription(
  reason: CsvImportResponse['duplicates'][number]['reason'],
) {
  return reason === 'existing_record'
    ? 'Matches a record already in your history.'
    : 'Matches an earlier row in this file.';
}

function ValidationReport({ report }: { report: CsvImportResponse }) {
  return (
    <section className="csv-report" aria-labelledby="csv-report-heading">
      <div className="record-form-card__heading">
        <p className="eyebrow">Server validation</p>
        <h2 id="csv-report-heading">Validation report</h2>
        <p>
          Duplicates are skipped records, not validation errors. CSV row
          contents are not displayed here.
        </p>
      </div>

      <dl className="csv-report__counts">
        <div>
          <dt>Total rows</dt>
          <dd>{report.total_rows}</dd>
        </div>
        <div>
          <dt>Valid rows</dt>
          <dd>{report.valid_rows}</dd>
        </div>
        <div>
          <dt>Invalid rows</dt>
          <dd>{report.invalid_rows}</dd>
        </div>
        <div>
          <dt>Duplicate rows</dt>
          <dd>{report.duplicate_rows}</dd>
        </div>
        <div>
          <dt>Ready rows</dt>
          <dd>{report.ready_rows}</dd>
        </div>
      </dl>

      {report.issues.length ? (
        <section
          className="csv-report__details"
          aria-labelledby="csv-issues-heading"
        >
          <h3 id="csv-issues-heading">Validation issues</h3>
          <ul>
            {report.issues.map((issue, index) => (
              <li
                key={`${issue.row_number ?? 'file'}-${issue.field ?? 'file'}-${issue.code}-${index}`}
              >
                <strong>
                  {issue.row_number === null
                    ? 'File issue'
                    : `Row ${issue.row_number}`}
                  {issue.field ? ` · ${issue.field}` : ''}
                </strong>
                <span>{issue.message}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : (
        <p className="inline-status">No validation issues were reported.</p>
      )}

      {report.duplicates.length ? (
        <section
          className="csv-report__details"
          aria-labelledby="csv-duplicates-heading"
        >
          <h3 id="csv-duplicates-heading">Duplicate rows</h3>
          <ul>
            {report.duplicates.map((duplicate) => (
              <li key={`${duplicate.row_number}-${duplicate.reason}`}>
                <strong>Row {duplicate.row_number}</strong>
                <span>{duplicateDescription(duplicate.reason)}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </section>
  );
}

export function CsvImportWorkflow() {
  const { accessToken, handleSessionError, refreshCurrentUser } = useAuth();
  const queryClient = useQueryClient();
  const fileReadSequence = useRef(0);
  const [recordType, setRecordType] = useState<CsvImportRecordType>('sleep');
  const [selectedCsv, setSelectedCsv] = useState<SelectedCsv | null>(null);
  const [validatedCsv, setValidatedCsv] = useState<ValidatedCsv | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [workflowError, setWorkflowError] = useState<string | null>(null);
  const [success, setSuccess] = useState<CsvImportResponse | null>(null);

  function resetResultState() {
    setValidatedCsv(null);
    setWorkflowError(null);
    setSuccess(null);
  }

  function handleApiError(error: unknown, action: 'validate' | 'commit') {
    if (error instanceof ApiError && error.code === 'profile_not_configured') {
      void refreshCurrentUser();
    }
    if (!handleSessionError(error)) {
      setWorkflowError(importErrorMessage(error, action));
    }
  }

  const validateMutation = useMutation({
    mutationFn: (request: CsvImportRequest) => {
      if (!accessToken) {
        throw new Error('Authenticated access token is unavailable');
      }
      return importWellnessCsv(accessToken, request);
    },
    retry: false,
    onSuccess: (report, request) => {
      setWorkflowError(null);
      setSuccess(null);
      setValidatedCsv({ request, report });
    },
    onError: (error) => handleApiError(error, 'validate'),
  });

  const commitMutation = useMutation({
    mutationFn: (request: CsvImportRequest) => {
      if (!accessToken) {
        throw new Error('Authenticated access token is unavailable');
      }
      return importWellnessCsv(accessToken, request);
    },
    retry: false,
    onSuccess: async (report, request) => {
      if (!report.can_commit) {
        setSuccess(null);
        setValidatedCsv({
          request: { ...request, mode: 'validate' },
          report,
        });
        setWorkflowError(
          'Server revalidation found issues, so no rows were imported. Review the updated report.',
        );
        return;
      }
      setWorkflowError(null);
      setSuccess(report);
      setValidatedCsv(null);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.records }),
        queryClient.invalidateQueries({ queryKey: queryKeys.summary }),
      ]);
    },
    onError: (error) => handleApiError(error, 'commit'),
  });

  const busy = validateMutation.isPending || commitMutation.isPending;

  async function selectFile(file: File | undefined) {
    const readId = ++fileReadSequence.current;
    resetResultState();
    setSelectedCsv(null);
    setFileError(null);
    if (!file) return;
    if (file.size > MAX_CSV_IMPORT_BYTES) {
      setFileError('Choose a CSV file no larger than 1 MB.');
      return;
    }

    try {
      const content = await file.text();
      if (readId !== fileReadSequence.current) return;
      const utf8Bytes = new TextEncoder().encode(content).byteLength;
      if (utf8Bytes > MAX_CSV_IMPORT_BYTES) {
        setFileError('Choose a CSV file no larger than 1 MB.');
        return;
      }
      if (!content.trim()) {
        setFileError('Choose a CSV file that contains a header and data.');
        return;
      }
      setSelectedCsv({ fileName: file.name, content, utf8Bytes });
    } catch {
      if (readId === fileReadSequence.current) {
        setFileError(
          'This CSV file could not be read. Choose it again or select another file.',
        );
      }
    }
  }

  function validateSelectedCsv() {
    if (!selectedCsv) {
      setFileError('Choose a CSV file before validation.');
      return;
    }
    validateMutation.mutate({
      schema_version: 1,
      record_type: recordType,
      mode: 'validate',
      content: selectedCsv.content,
    });
  }

  function commitValidatedCsv() {
    if (!validatedCsv) return;
    commitMutation.mutate({
      ...validatedCsv.request,
      mode: 'commit',
    });
  }

  const canImport = Boolean(
    validatedCsv?.report.can_commit && validatedCsv.report.ready_rows > 0,
  );

  return (
    <div className="csv-import-workflow">
      <section className="record-form-card" aria-labelledby="csv-setup-heading">
        <div className="record-form-card__heading">
          <p className="eyebrow">CSV schema v1</p>
          <h2 id="csv-setup-heading">Select and validate a CSV</h2>
          <p>
            Choose one supported category per file. LifeLenz validates the
            complete document on the server before anything can be imported.
          </p>
        </div>

        <div className="record-form">
          <label className="field">
            <span>Record category</span>
            <select
              value={recordType}
              disabled={busy}
              onChange={(event) => {
                setRecordType(event.target.value as CsvImportRecordType);
                resetResultState();
              }}
            >
              {csvImportRecordTypes.map((type) => (
                <option key={type} value={type}>
                  {csvImportRecordTypeLabels[type]}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>CSV file</span>
            <input
              type="file"
              accept=".csv,text/csv"
              disabled={busy}
              onChange={(event) => void selectFile(event.target.files?.[0])}
            />
          </label>

          {selectedCsv ? (
            <p className="csv-file-summary" role="status">
              Selected <strong>{selectedCsv.fileName}</strong> ·{' '}
              {selectedCsv.utf8Bytes.toLocaleString()} UTF-8 bytes
            </p>
          ) : null}
          {fileError ? <Alert>{fileError}</Alert> : null}
          {workflowError ? <Alert>{workflowError}</Alert> : null}
          {success ? (
            <Alert tone="success">
              Import confirmed: {success.imported_rows} row
              {success.imported_rows === 1 ? '' : 's'} imported and{' '}
              {success.duplicate_rows} duplicate
              {success.duplicate_rows === 1 ? '' : 's'} skipped.
            </Alert>
          ) : null}

          {busy ? (
            <p className="inline-status" role="status" aria-live="polite">
              {validateMutation.isPending
                ? 'Validating CSV…'
                : 'Importing ready rows…'}
            </p>
          ) : null}

          <div className="record-form__actions">
            <p>
              Validation never writes records. A separate import action is
              required after a successful report.
            </p>
            <button
              type="button"
              className="button button--primary"
              disabled={!selectedCsv || busy}
              onClick={validateSelectedCsv}
            >
              Validate CSV
            </button>
          </div>
        </div>
      </section>

      {validatedCsv ? (
        <>
          <ValidationReport report={validatedCsv.report} />
          <section
            className="csv-import-action"
            aria-labelledby="csv-import-heading"
          >
            <h2 id="csv-import-heading">Ready to import</h2>
            {validatedCsv.report.can_commit ? (
              validatedCsv.report.ready_rows > 0 ? (
                <p>
                  {validatedCsv.report.ready_rows} unique row
                  {validatedCsv.report.ready_rows === 1 ? ' is' : 's are'}{' '}
                  ready. The server will validate the CSV again during import.
                </p>
              ) : (
                <p>There are no unique rows to import.</p>
              )
            ) : (
              <p>
                Resolve the validation issues outside LifeLenz, then select and
                validate the corrected file.
              </p>
            )}
            {canImport ? (
              <button
                type="button"
                className="button button--primary"
                disabled={busy}
                onClick={commitValidatedCsv}
              >
                Import ready rows
              </button>
            ) : null}
          </section>
        </>
      ) : null}

      <details className="csv-format-help">
        <summary>CSV format help</summary>
        <div>
          <p>
            CSV schema v1 accepts one category per file, up to 1 MB and 5,000
            nonblank rows. Required timestamps must include an explicit timezone
            offset.
          </p>
          <p>
            Supported categories are Sleep, Daily activity, Hydration, Daily
            nutrition, Body measurement, and Wellness check-in. Consult the
            project CSV schema v1 documentation for exact headers.
          </p>
        </div>
      </details>
    </div>
  );
}
