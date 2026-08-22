import { useState, type FormEvent } from 'react';

import type {
  CheckInTag,
  MoodCategory,
  SubjectiveCheckInCreateRequest,
} from '../../api/types';
import { Alert } from '../../components/Alert';
import { Button } from '../../components/Button';
import { currentLocalDateTime } from '../dateTime';
import { checkInEditValue } from '../recordEditing';
import {
  buildSubjectiveCheckInRequest,
  type CheckInFormValue,
} from '../recordRequests';
import type { RecordFormProps } from './formTypes';
import { NotesField } from './NotesField';

const scores = Array.from({ length: 10 }, (_, index) => index + 1);
const moodCategories: ReadonlyArray<{ value: MoodCategory; label: string }> = [
  { value: 'very_low', label: 'Very low' },
  { value: 'low', label: 'Low' },
  { value: 'neutral', label: 'Neutral' },
  { value: 'high', label: 'High' },
  { value: 'very_high', label: 'Very high' },
];
const tagOptions: ReadonlyArray<{ value: CheckInTag; label: string }> = [
  { value: 'rested', label: 'Rested' },
  { value: 'tired', label: 'Tired' },
  { value: 'focused', label: 'Focused' },
  { value: 'distracted', label: 'Distracted' },
  { value: 'calm', label: 'Calm' },
  { value: 'tense', label: 'Tense' },
  { value: 'motivated', label: 'Motivated' },
  { value: 'unmotivated', label: 'Unmotivated' },
  { value: 'social', label: 'Social' },
  { value: 'solitary', label: 'Solitary' },
  { value: 'other', label: 'Other' },
];

function initialCheckInValue(): CheckInFormValue {
  return {
    recordedAt: currentLocalDateTime(),
    mood: '',
    energy: '',
    stress: '',
    motivation: '',
    moodCategory: '',
    tags: [],
    notes: '',
  };
}

function ScoreField({
  id,
  label,
  value,
  disabled,
  onChange,
  optional = false,
}: {
  id: string;
  label: string;
  value: string;
  disabled: boolean;
  onChange(value: string): void;
  optional?: boolean;
}) {
  return (
    <div className="field">
      <label htmlFor={id}>{`${label}${optional ? ' (optional)' : ''}`}</label>
      <select
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        required={!optional}
        disabled={disabled}
        aria-describedby={`${id}-hint`}
      >
        <option value="">{optional ? 'Not recorded' : 'Choose 1–10'}</option>
        {scores.map((score) => (
          <option key={score} value={score}>
            {score}
          </option>
        ))}
      </select>
      <span className="field__hint" id={`${id}-hint`}>
        1 is the lower end and 10 is the higher end of your own scale.
      </span>
    </div>
  );
}

export function SubjectiveCheckInForm({
  isSaving,
  initialRecord,
  onSubmit,
}: RecordFormProps) {
  const [value, setValue] = useState(
    () => checkInEditValue(initialRecord) ?? initialCheckInValue(),
  );
  const [error, setError] = useState<string | null>(null);

  function toggleTag(tag: CheckInTag) {
    setValue((current) => ({
      ...current,
      tags: current.tags.includes(tag)
        ? current.tags.filter((item) => item !== tag)
        : [...current.tags, tag],
    }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    let request: SubjectiveCheckInCreateRequest;
    try {
      request = buildSubjectiveCheckInRequest(value);
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
        <div className="field">
          <label htmlFor="check-in-recorded-at">Recorded at</label>
          <input
            id="check-in-recorded-at"
            type="datetime-local"
            value={value.recordedAt}
            onChange={(event) =>
              setValue({ ...value, recordedAt: event.target.value })
            }
            required
            disabled={isSaving}
          />
        </div>
        <ScoreField
          id="mood-score"
          label="Mood score"
          value={value.mood}
          onChange={(mood) => setValue({ ...value, mood })}
          disabled={isSaving}
        />
        <ScoreField
          id="energy-score"
          label="Energy score"
          value={value.energy}
          onChange={(energy) => setValue({ ...value, energy })}
          disabled={isSaving}
        />
        <ScoreField
          id="stress-score"
          label="Stress score"
          value={value.stress}
          onChange={(stress) => setValue({ ...value, stress })}
          disabled={isSaving}
        />
        <ScoreField
          id="motivation-score"
          label="Motivation score"
          value={value.motivation}
          onChange={(motivation) => setValue({ ...value, motivation })}
          disabled={isSaving}
          optional
        />
        <div className="field">
          <label htmlFor="mood-category">Mood description (optional)</label>
          <select
            id="mood-category"
            value={value.moodCategory}
            onChange={(event) =>
              setValue({
                ...value,
                moodCategory: event.target.value as MoodCategory | '',
              })
            }
            disabled={isSaving}
          >
            <option value="">Not recorded</option>
            {moodCategories.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>
      <fieldset className="record-form__tags">
        <legend>Context tags (optional)</legend>
        <div>
          {tagOptions.map((option) => (
            <label key={option.value}>
              <input
                type="checkbox"
                checked={value.tags.includes(option.value)}
                onChange={() => toggleTag(option.value)}
                disabled={isSaving}
              />
              {option.label}
            </label>
          ))}
        </div>
      </fieldset>
      <NotesField
        value={value.notes}
        disabled={isSaving}
        onChange={(notes) => setValue({ ...value, notes })}
      />
      <div className="record-form__actions">
        <Button type="submit" disabled={isSaving}>
          {isSaving ? 'Saving…' : 'Save wellness check-in'}
        </Button>
        <p>Scores describe your own report and are not medical assessments.</p>
      </div>
    </form>
  );
}
