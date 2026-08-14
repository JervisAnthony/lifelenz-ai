import { useState, type FormEvent } from 'react';

import type { DailyActivityRecordCreateRequest } from '../../api/types';
import { Alert } from '../../components/Alert';
import { Button } from '../../components/Button';
import { Field } from '../../components/Field';
import { currentLocalDateTime } from '../dateTime';
import {
  buildDailyActivityRecordRequest,
  type DailyActivityFormValue,
} from '../recordRequests';
import type { RecordFormProps } from './formTypes';
import { NotesField } from './NotesField';

function initialDailyActivityValue(): DailyActivityFormValue {
  const now = currentLocalDateTime();
  return {
    recordedAt: now,
    activityDate: now.slice(0, 10),
    steps: '',
    distanceKilometers: '',
    activeMinutes: '',
    activeCaloriesKcal: '',
    notes: '',
  };
}

export function DailyActivityRecordForm({
  isSaving,
  onSubmit,
}: RecordFormProps) {
  const [value, setValue] = useState(initialDailyActivityValue);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    let request: DailyActivityRecordCreateRequest;
    try {
      request = buildDailyActivityRecordRequest(value);
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
          id="activity-recorded-at"
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
          id="activity-date"
          label="Activity date"
          type="date"
          value={value.activityDate}
          onChange={(event) =>
            setValue({ ...value, activityDate: event.target.value })
          }
          required
          disabled={isSaving}
        />
      </div>
      <fieldset className="record-form__fieldset">
        <legend>Daily totals (optional)</legend>
        <div className="record-form__grid">
          <Field
            id="activity-steps"
            label="Steps"
            type="number"
            min="0"
            step="1"
            value={value.steps}
            onChange={(event) =>
              setValue({ ...value, steps: event.target.value })
            }
            disabled={isSaving}
          />
          <Field
            id="activity-distance"
            label="Distance (kilometers)"
            type="number"
            min="0"
            step="0.01"
            value={value.distanceKilometers}
            onChange={(event) =>
              setValue({ ...value, distanceKilometers: event.target.value })
            }
            disabled={isSaving}
          />
          <Field
            id="activity-minutes"
            label="Active minutes"
            type="number"
            min="0"
            step="0.01"
            value={value.activeMinutes}
            onChange={(event) =>
              setValue({ ...value, activeMinutes: event.target.value })
            }
            disabled={isSaving}
          />
          <Field
            id="activity-calories"
            label="Active calories (kcal)"
            type="number"
            min="0"
            step="0.01"
            value={value.activeCaloriesKcal}
            onChange={(event) =>
              setValue({ ...value, activeCaloriesKcal: event.target.value })
            }
            disabled={isSaving}
          />
        </div>
      </fieldset>
      <NotesField
        value={value.notes}
        disabled={isSaving}
        onChange={(notes) => setValue({ ...value, notes })}
      />
      <div className="record-form__actions">
        <Button type="submit" disabled={isSaving}>
          {isSaving ? 'Saving…' : 'Save daily activity record'}
        </Button>
        <p>Totals are stored in the canonical units shown.</p>
      </div>
    </form>
  );
}
