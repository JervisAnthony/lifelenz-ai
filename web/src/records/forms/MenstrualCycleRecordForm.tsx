import { useState, type FormEvent } from 'react';

import type { MenstrualCycleRecordCreateRequest } from '../../api/types';
import { Alert } from '../../components/Alert';
import { Button } from '../../components/Button';
import { Field } from '../../components/Field';
import { currentLocalDateTime } from '../dateTime';
import { menstrualCycleEditValue } from '../recordEditing';
import {
  buildMenstrualCycleRecordRequest,
  type MenstrualCycleFormValue,
} from '../recordRequests';
import type { RecordFormProps } from './formTypes';
import { NotesField } from './NotesField';

function initialCycleValue(): MenstrualCycleFormValue {
  const now = currentLocalDateTime();
  return {
    recordedAt: now,
    startDate: now.slice(0, 10),
    endDate: '',
    notes: '',
  };
}

export function MenstrualCycleRecordForm({
  isSaving,
  initialRecord,
  onSubmit,
}: RecordFormProps) {
  const [value, setValue] = useState(
    () => menstrualCycleEditValue(initialRecord) ?? initialCycleValue(),
  );
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    let request: MenstrualCycleRecordCreateRequest;
    try {
      request = buildMenstrualCycleRecordRequest(value);
    } catch (caughtError) {
      if (caughtError instanceof Error) {
        setError(caughtError.message);
      }
      return;
    }
    await onSubmit(request).catch(() => undefined);
  }

  return (
    <form
      className="record-form"
      onSubmit={(event) => void handleSubmit(event)}
    >
      {error ? <Alert>{error}</Alert> : null}
      <div className="record-form__grid">
        <Field
          id="cycle-recorded-at"
          label="Recorded at"
          type="datetime-local"
          value={value.recordedAt}
          onChange={(event) =>
            setValue({ ...value, recordedAt: event.target.value })
          }
          required
          disabled={isSaving}
        />
        <Field
          id="cycle-start-date"
          label="Cycle start date"
          type="date"
          value={value.startDate}
          onChange={(event) =>
            setValue({ ...value, startDate: event.target.value })
          }
          required
          disabled={isSaving}
        />
        <Field
          id="cycle-end-date"
          label="Cycle end date (optional)"
          type="date"
          min={value.startDate || undefined}
          value={value.endDate}
          onChange={(event) =>
            setValue({ ...value, endDate: event.target.value })
          }
          hint="Leave blank when no end date is recorded."
          disabled={isSaving}
        />
      </div>
      <NotesField
        value={value.notes}
        disabled={isSaving}
        onChange={(notes) => setValue({ ...value, notes })}
      />
      <div className="record-form__actions">
        <Button type="submit" disabled={isSaving}>
          {isSaving ? 'Saving…' : 'Save menstrual cycle'}
        </Button>
        <p>
          Dates are stored as supplied without prediction or classification.
        </p>
      </div>
    </form>
  );
}
