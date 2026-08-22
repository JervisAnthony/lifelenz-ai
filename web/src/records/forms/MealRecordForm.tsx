import { useState, type FormEvent } from 'react';

import type { MealRecordCreateRequest, MealType } from '../../api/types';
import { Alert } from '../../components/Alert';
import { Button } from '../../components/Button';
import { Field } from '../../components/Field';
import { currentLocalDateTime } from '../dateTime';
import { mealEditValue } from '../recordEditing';
import { buildMealRecordRequest, type MealFormValue } from '../recordRequests';
import type { RecordFormProps } from './formTypes';
import { NotesField } from './NotesField';
import { NutritionFields } from './NutritionFields';

const mealTypeOptions: ReadonlyArray<{ value: MealType; label: string }> = [
  { value: 'breakfast', label: 'Breakfast' },
  { value: 'lunch', label: 'Lunch' },
  { value: 'dinner', label: 'Dinner' },
  { value: 'snack', label: 'Snack' },
  { value: 'other', label: 'Other' },
];

function initialMealValue(): MealFormValue {
  return {
    recordedAt: currentLocalDateTime(),
    mealType: '',
    name: '',
    nutrition: {
      caloriesKcal: '',
      proteinGrams: '',
      carbohydratesGrams: '',
      fatGrams: '',
      fibreGrams: '',
    },
    notes: '',
  };
}

export function MealRecordForm({
  isSaving,
  initialRecord,
  onSubmit,
}: RecordFormProps) {
  const [value, setValue] = useState(
    () => mealEditValue(initialRecord) ?? initialMealValue(),
  );
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    let request: MealRecordCreateRequest;
    try {
      request = buildMealRecordRequest(value);
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
          id="meal-recorded-at"
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
          <label htmlFor="meal-type">Meal type</label>
          <select
            id="meal-type"
            value={value.mealType}
            onChange={(event) =>
              setValue({
                ...value,
                mealType: event.target.value as MealType | '',
              })
            }
            required
            disabled={isSaving}
          >
            <option value="">Choose a meal type</option>
            {mealTypeOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        <Field
          id="meal-name"
          label="Meal name (optional)"
          type="text"
          value={value.name}
          onChange={(event) => setValue({ ...value, name: event.target.value })}
          hint="A descriptive name only; nutrition values are entered separately."
          disabled={isSaving}
        />
      </div>
      <NutritionFields
        value={value.nutrition}
        disabled={isSaving}
        onChange={(field, fieldValue) =>
          setValue({
            ...value,
            nutrition: { ...value.nutrition, [field]: fieldValue },
          })
        }
      />
      <NotesField
        value={value.notes}
        disabled={isSaving}
        onChange={(notes) => setValue({ ...value, notes })}
      />
      <div className="record-form__actions">
        <Button type="submit" disabled={isSaving}>
          {isSaving ? 'Saving…' : 'Save meal record'}
        </Button>
        <p>
          Measurements are recorded as supplied without food classification.
        </p>
      </div>
    </form>
  );
}
