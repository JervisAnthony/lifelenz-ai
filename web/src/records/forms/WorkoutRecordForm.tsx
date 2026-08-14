import { useState, type FormEvent } from 'react';

import type { WorkoutRecordCreateRequest, WorkoutType } from '../../api/types';
import { Alert } from '../../components/Alert';
import { Button } from '../../components/Button';
import { Field } from '../../components/Field';
import { currentLocalDateTime } from '../dateTime';
import {
  buildWorkoutRecordRequest,
  type WorkoutFormValue,
} from '../recordRequests';
import type { RecordFormProps } from './formTypes';
import { NotesField } from './NotesField';

const workoutTypeOptions: ReadonlyArray<{
  value: WorkoutType;
  label: string;
}> = [
  { value: 'walking', label: 'Walking' },
  { value: 'running', label: 'Running' },
  { value: 'cycling', label: 'Cycling' },
  { value: 'swimming', label: 'Swimming' },
  { value: 'strength_training', label: 'Strength training' },
  { value: 'yoga', label: 'Yoga' },
  { value: 'hiking', label: 'Hiking' },
  { value: 'rowing', label: 'Rowing' },
  { value: 'elliptical', label: 'Elliptical' },
  { value: 'sport', label: 'Sport' },
  { value: 'other', label: 'Other' },
];

function initialWorkoutValue(): WorkoutFormValue {
  const now = new Date();
  return {
    start: currentLocalDateTime(new Date(now.getTime() - 60 * 60 * 1000)),
    end: currentLocalDateTime(now),
    workoutType: 'walking',
    distanceKilometers: '',
    activeCaloriesKcal: '',
    perceivedExertion: '',
    averageHeartRateBpm: '',
    notes: '',
  };
}

export function WorkoutRecordForm({ isSaving, onSubmit }: RecordFormProps) {
  const [value, setValue] = useState(initialWorkoutValue);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    let request: WorkoutRecordCreateRequest;
    try {
      request = buildWorkoutRecordRequest(value);
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
          id="workout-start"
          label="Workout start"
          type="datetime-local"
          value={value.start}
          onChange={(event) =>
            setValue({ ...value, start: event.target.value })
          }
          required
          disabled={isSaving}
        />
        <Field
          id="workout-end"
          label="Workout end"
          type="datetime-local"
          value={value.end}
          onChange={(event) => setValue({ ...value, end: event.target.value })}
          required
          disabled={isSaving}
        />
        <div className="field">
          <label htmlFor="workout-type">Workout type</label>
          <select
            id="workout-type"
            value={value.workoutType}
            onChange={(event) =>
              setValue({
                ...value,
                workoutType: event.target.value as WorkoutType,
              })
            }
            disabled={isSaving}
          >
            {workoutTypeOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>
      <fieldset className="record-form__fieldset">
        <legend>Workout measurements (optional)</legend>
        <div className="record-form__grid">
          <Field
            id="workout-distance"
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
            id="workout-calories"
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
          <Field
            id="workout-exertion"
            label="Perceived exertion (1–10)"
            type="number"
            min="1"
            max="10"
            step="1"
            value={value.perceivedExertion}
            onChange={(event) =>
              setValue({ ...value, perceivedExertion: event.target.value })
            }
            disabled={isSaving}
          />
          <Field
            id="workout-heart-rate"
            label="Average heart rate (bpm)"
            type="number"
            min="0.01"
            step="0.01"
            value={value.averageHeartRateBpm}
            onChange={(event) =>
              setValue({ ...value, averageHeartRateBpm: event.target.value })
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
          {isSaving ? 'Saving…' : 'Save workout record'}
        </Button>
        <p>Times use your browser’s local UTC offset.</p>
      </div>
    </form>
  );
}
