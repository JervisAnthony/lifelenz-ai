import { useState, type FormEvent } from 'react';

import type { SleepQuality, SleepRecordCreateRequest } from '../../api/types';
import { Alert } from '../../components/Alert';
import { Button } from '../../components/Button';
import { Field } from '../../components/Field';
import { currentLocalDateTime } from '../dateTime';
import {
  buildSleepRecordRequest,
  type SleepFormValue,
} from '../recordRequests';
import type { RecordFormProps } from './formTypes';
import { NotesField } from './NotesField';

const qualityOptions: ReadonlyArray<{
  value: SleepQuality;
  label: string;
}> = [
  { value: 'very_poor', label: 'Very poor' },
  { value: 'poor', label: 'Poor' },
  { value: 'fair', label: 'Fair' },
  { value: 'good', label: 'Good' },
  { value: 'very_good', label: 'Very good' },
];

function initialSleepValue(): SleepFormValue {
  const now = new Date();
  return {
    start: currentLocalDateTime(new Date(now.getTime() - 8 * 60 * 60 * 1000)),
    end: currentLocalDateTime(now),
    sleepMinutes: '',
    awakeMinutes: '0',
    quality: '',
    interruptionCount: '',
    notes: '',
  };
}

export function SleepRecordForm({ isSaving, onSubmit }: RecordFormProps) {
  const [value, setValue] = useState(initialSleepValue);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    let request: SleepRecordCreateRequest;
    try {
      request = buildSleepRecordRequest(value);
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
          id="sleep-start"
          label="Sleep start"
          type="datetime-local"
          value={value.start}
          onChange={(event) =>
            setValue({ ...value, start: event.target.value })
          }
          required
          disabled={isSaving}
        />
        <Field
          id="sleep-end"
          label="Sleep end"
          type="datetime-local"
          value={value.end}
          onChange={(event) => setValue({ ...value, end: event.target.value })}
          required
          disabled={isSaving}
        />
        <Field
          id="sleep-minutes"
          label="Minutes asleep"
          type="number"
          min="0.01"
          step="0.01"
          value={value.sleepMinutes}
          onChange={(event) =>
            setValue({ ...value, sleepMinutes: event.target.value })
          }
          required
          disabled={isSaving}
        />
        <Field
          id="awake-minutes"
          label="Minutes awake"
          type="number"
          min="0"
          step="0.01"
          value={value.awakeMinutes}
          onChange={(event) =>
            setValue({ ...value, awakeMinutes: event.target.value })
          }
          required
          disabled={isSaving}
        />
        <div className="field">
          <label htmlFor="sleep-quality">Sleep quality (optional)</label>
          <select
            id="sleep-quality"
            value={value.quality}
            onChange={(event) =>
              setValue({
                ...value,
                quality: event.target.value as SleepQuality | '',
              })
            }
            disabled={isSaving}
          >
            <option value="">Not recorded</option>
            {qualityOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        <Field
          id="sleep-interruptions"
          label="Interruptions (optional)"
          type="number"
          min="0"
          step="1"
          value={value.interruptionCount}
          onChange={(event) =>
            setValue({ ...value, interruptionCount: event.target.value })
          }
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
          {isSaving ? 'Saving…' : 'Save sleep record'}
        </Button>
        <p>Times are saved with your browser’s local UTC offset.</p>
      </div>
    </form>
  );
}
