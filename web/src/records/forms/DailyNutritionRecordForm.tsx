import { useState, type FormEvent } from 'react';

import type { DailyNutritionRecordCreateRequest } from '../../api/types';
import { Alert } from '../../components/Alert';
import { Button } from '../../components/Button';
import { Field } from '../../components/Field';
import { currentLocalDateTime } from '../dateTime';
import { dailyNutritionEditValue } from '../recordEditing';
import {
  buildDailyNutritionRecordRequest,
  type DailyNutritionFormValue,
} from '../recordRequests';
import type { RecordFormProps } from './formTypes';
import { NotesField } from './NotesField';
import { NutritionFields } from './NutritionFields';

function initialDailyNutritionValue(): DailyNutritionFormValue {
  const now = currentLocalDateTime();
  return {
    recordedAt: now,
    nutritionDate: now.slice(0, 10),
    mealCount: '',
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

export function DailyNutritionRecordForm({
  isSaving,
  initialRecord,
  onSubmit,
}: RecordFormProps) {
  const [value, setValue] = useState(
    () => dailyNutritionEditValue(initialRecord) ?? initialDailyNutritionValue(),
  );
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    let request: DailyNutritionRecordCreateRequest;
    try {
      request = buildDailyNutritionRecordRequest(value);
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
          id="daily-nutrition-recorded-at"
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
          id="nutrition-date"
          label="Nutrition date"
          type="date"
          value={value.nutritionDate}
          onChange={(event) =>
            setValue({ ...value, nutritionDate: event.target.value })
          }
          required
          disabled={isSaving}
        />
        <Field
          id="nutrition-meal-count"
          label="Meal count (optional)"
          type="number"
          min="0"
          step="1"
          value={value.mealCount}
          onChange={(event) =>
            setValue({ ...value, mealCount: event.target.value })
          }
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
          {isSaving ? 'Saving…' : 'Save daily nutrition record'}
        </Button>
        <p>These are user-supplied totals for the selected calendar date.</p>
      </div>
    </form>
  );
}
