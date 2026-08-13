import { useState, type FormEvent } from 'react';

import type {
  BeverageType,
  HydrationRecordCreateRequest,
} from '../../api/types';
import { Alert } from '../../components/Alert';
import { Button } from '../../components/Button';
import { Field } from '../../components/Field';
import { currentLocalDateTime } from '../dateTime';
import {
  buildHydrationRecordRequest,
  type HydrationFormValue,
} from '../recordRequests';
import type { RecordFormProps } from './formTypes';
import { NotesField } from './NotesField';

const beverageOptions: ReadonlyArray<{
  value: BeverageType;
  label: string;
}> = [
  { value: 'water', label: 'Water' },
  { value: 'sparkling_water', label: 'Sparkling water' },
  { value: 'tea', label: 'Tea' },
  { value: 'coffee', label: 'Coffee' },
  { value: 'juice', label: 'Juice' },
  { value: 'milk', label: 'Milk' },
  { value: 'sports_drink', label: 'Sports drink' },
  { value: 'other', label: 'Other' },
];

function initialHydrationValue(): HydrationFormValue {
  return {
    recordedAt: currentLocalDateTime(),
    volume: '',
    beverageType: 'water',
    caffeine: '',
    notes: '',
  };
}

export function HydrationRecordForm({ isSaving, onSubmit }: RecordFormProps) {
  const [value, setValue] = useState(initialHydrationValue);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    let request: HydrationRecordCreateRequest;
    try {
      request = buildHydrationRecordRequest(value);
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
          id="hydration-recorded-at"
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
          id="hydration-volume"
          label="Volume (milliliters)"
          type="number"
          min="0.01"
          step="0.01"
          value={value.volume}
          onChange={(event) =>
            setValue({ ...value, volume: event.target.value })
          }
          hint="Stored in the backend’s canonical milliliter unit."
          required
          disabled={isSaving}
        />
        <div className="field">
          <label htmlFor="beverage-type">Beverage</label>
          <select
            id="beverage-type"
            value={value.beverageType}
            onChange={(event) =>
              setValue({
                ...value,
                beverageType: event.target.value as BeverageType,
              })
            }
            disabled={isSaving}
          >
            {beverageOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        <Field
          id="caffeine-milligrams"
          label="Caffeine in milligrams (optional)"
          type="number"
          min="0"
          step="0.01"
          value={value.caffeine}
          onChange={(event) =>
            setValue({ ...value, caffeine: event.target.value })
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
          {isSaving ? 'Saving…' : 'Save hydration record'}
        </Button>
        <p>LifeLenz records the amount you report without setting a target.</p>
      </div>
    </form>
  );
}
