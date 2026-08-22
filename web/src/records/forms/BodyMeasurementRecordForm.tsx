import { useState, type FormEvent } from 'react';

import type { BodyMeasurementRecordCreateRequest } from '../../api/types';
import { Alert } from '../../components/Alert';
import { Button } from '../../components/Button';
import { Field } from '../../components/Field';
import { currentLocalDateTime } from '../dateTime';
import { bodyMeasurementEditValue } from '../recordEditing';
import {
  buildBodyMeasurementRecordRequest,
  type BodyMeasurementFormValue,
} from '../recordRequests';
import type { RecordFormProps } from './formTypes';
import { NotesField } from './NotesField';

function initialBodyMeasurementValue(): BodyMeasurementFormValue {
  return {
    recordedAt: currentLocalDateTime(),
    weightKilograms: '',
    heightMeters: '',
    bodyFatPercent: '',
    waistCircumferenceCentimeters: '',
    notes: '',
  };
}

export function BodyMeasurementRecordForm({
  isSaving,
  initialRecord,
  onSubmit,
}: RecordFormProps) {
  const [value, setValue] = useState(
    () => bodyMeasurementEditValue(initialRecord) ?? initialBodyMeasurementValue(),
  );
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    let request: BodyMeasurementRecordCreateRequest;
    try {
      request = buildBodyMeasurementRecordRequest(value);
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
      <Field
        id="body-recorded-at"
        label="Recorded at"
        type="datetime-local"
        value={value.recordedAt}
        onChange={(event) =>
          setValue({ ...value, recordedAt: event.target.value })
        }
        required
        disabled={isSaving}
      />
      <fieldset className="record-form__fieldset">
        <legend>Measurements</legend>
        <div className="record-form__grid">
          <Field
            id="body-weight"
            label="Weight (kilograms)"
            type="number"
            min="0.01"
            step="0.01"
            value={value.weightKilograms}
            onChange={(event) =>
              setValue({ ...value, weightKilograms: event.target.value })
            }
            required
            disabled={isSaving}
          />
          <Field
            id="body-height"
            label="Height (meters, optional)"
            type="number"
            min="0.01"
            step="0.01"
            value={value.heightMeters}
            onChange={(event) =>
              setValue({ ...value, heightMeters: event.target.value })
            }
            disabled={isSaving}
          />
          <Field
            id="body-fat"
            label="Body fat (percent, optional)"
            type="number"
            min="0"
            max="100"
            step="0.01"
            value={value.bodyFatPercent}
            onChange={(event) =>
              setValue({ ...value, bodyFatPercent: event.target.value })
            }
            disabled={isSaving}
          />
          <Field
            id="body-waist"
            label="Waist circumference (centimeters, optional)"
            type="number"
            min="0.01"
            step="0.01"
            value={value.waistCircumferenceCentimeters}
            onChange={(event) =>
              setValue({
                ...value,
                waistCircumferenceCentimeters: event.target.value,
              })
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
          {isSaving ? 'Saving…' : 'Save body measurement'}
        </Button>
        <p>Measurements are stored without classification or interpretation.</p>
      </div>
    </form>
  );
}
