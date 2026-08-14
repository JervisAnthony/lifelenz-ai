import { useState, type FormEvent } from 'react';

import type {
  CycleSymptom,
  MenstrualBleedingRecordCreateRequest,
  MenstrualFlow,
  SymptomIntensity,
} from '../../api/types';
import { Alert } from '../../components/Alert';
import { Button } from '../../components/Button';
import { Field } from '../../components/Field';
import { currentLocalDateTime } from '../dateTime';
import {
  buildMenstrualBleedingRecordRequest,
  type MenstrualBleedingFormValue,
} from '../recordRequests';
import type { RecordFormProps } from './formTypes';
import { NotesField } from './NotesField';

const flowOptions: ReadonlyArray<{ value: MenstrualFlow; label: string }> = [
  { value: 'spotting', label: 'Spotting' },
  { value: 'light', label: 'Light' },
  { value: 'moderate', label: 'Moderate' },
  { value: 'heavy', label: 'Heavy' },
];

const symptomOptions: ReadonlyArray<{
  value: CycleSymptom;
  label: string;
}> = [
  { value: 'cramps', label: 'Cramps' },
  { value: 'bloating', label: 'Bloating' },
  { value: 'headache', label: 'Headache' },
  { value: 'back_discomfort', label: 'Back discomfort' },
  { value: 'breast_tenderness', label: 'Breast tenderness' },
  { value: 'fatigue', label: 'Fatigue' },
  { value: 'mood_change', label: 'Mood change' },
  { value: 'nausea', label: 'Nausea' },
  { value: 'acne', label: 'Acne' },
  { value: 'food_craving', label: 'Food craving' },
  { value: 'sleep_change', label: 'Sleep change' },
  { value: 'other', label: 'Other' },
];

const intensityOptions: ReadonlyArray<{
  value: SymptomIntensity;
  label: string;
}> = [
  { value: 'mild', label: 'Mild' },
  { value: 'moderate', label: 'Moderate' },
  { value: 'strong', label: 'Strong' },
];

function initialBleedingValue(): MenstrualBleedingFormValue {
  return {
    recordedAt: currentLocalDateTime(),
    flow: '',
    symptoms: [],
    notes: '',
  };
}

export function MenstrualBleedingRecordForm({
  isSaving,
  onSubmit,
}: RecordFormProps) {
  const [value, setValue] = useState(initialBleedingValue);
  const [error, setError] = useState<string | null>(null);

  function toggleSymptom(symptom: CycleSymptom) {
    setValue((current) => ({
      ...current,
      symptoms: current.symptoms.some((entry) => entry.symptom === symptom)
        ? current.symptoms.filter((entry) => entry.symptom !== symptom)
        : [...current.symptoms, { symptom, intensity: '' }],
    }));
  }

  function setIntensity(
    symptom: CycleSymptom,
    intensity: SymptomIntensity | '',
  ) {
    setValue((current) => ({
      ...current,
      symptoms: current.symptoms.map((entry) =>
        entry.symptom === symptom ? { ...entry, intensity } : entry,
      ),
    }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    let request: MenstrualBleedingRecordCreateRequest;
    try {
      request = buildMenstrualBleedingRecordRequest(value);
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
          id="bleeding-recorded-at"
          label="Recorded at"
          type="datetime-local"
          value={value.recordedAt}
          onChange={(event) =>
            setValue({ ...value, recordedAt: event.target.value })
          }
          required
          disabled={isSaving}
        />
        <div className="field">
          <label htmlFor="menstrual-flow">Flow description</label>
          <select
            id="menstrual-flow"
            value={value.flow}
            onChange={(event) =>
              setValue({
                ...value,
                flow: event.target.value as MenstrualFlow | '',
              })
            }
            required
            disabled={isSaving}
          >
            <option value="">Choose a flow description</option>
            {flowOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>
      <fieldset className="record-form__fieldset menstrual-symptoms">
        <legend>Symptoms (optional)</legend>
        <div className="menstrual-symptoms__list">
          {symptomOptions.map((option) => {
            const selected = value.symptoms.find(
              (entry) => entry.symptom === option.value,
            );
            const checkboxId = `cycle-symptom-${option.value}`;
            const intensityId = `${checkboxId}-intensity`;
            return (
              <div className="menstrual-symptom" key={option.value}>
                <label htmlFor={checkboxId}>
                  <input
                    id={checkboxId}
                    type="checkbox"
                    checked={Boolean(selected)}
                    onChange={() => toggleSymptom(option.value)}
                    disabled={isSaving}
                  />
                  {option.label}
                </label>
                {selected ? (
                  <div className="field menstrual-symptom__intensity">
                    <label htmlFor={intensityId}>
                      Intensity for {option.label.toLowerCase()} (optional)
                    </label>
                    <select
                      id={intensityId}
                      value={selected.intensity}
                      onChange={(event) =>
                        setIntensity(
                          option.value,
                          event.target.value as SymptomIntensity | '',
                        )
                      }
                      disabled={isSaving}
                    >
                      <option value="">Not recorded</option>
                      {intensityOptions.map((intensity) => (
                        <option key={intensity.value} value={intensity.value}>
                          {intensity.label}
                        </option>
                      ))}
                    </select>
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      </fieldset>
      <NotesField
        value={value.notes}
        disabled={isSaving}
        onChange={(notes) => setValue({ ...value, notes })}
      />
      <div className="record-form__actions">
        <Button type="submit" disabled={isSaving}>
          {isSaving ? 'Saving…' : 'Save bleeding observation'}
        </Button>
        <p>Recent records identify this entry without showing its details.</p>
      </div>
    </form>
  );
}
