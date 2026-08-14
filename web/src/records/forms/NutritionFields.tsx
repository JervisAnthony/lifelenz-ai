import { Field } from '../../components/Field';
import type { NutritionFormValue } from '../recordRequests';

const nutritionFields: ReadonlyArray<{
  key: keyof NutritionFormValue;
  id: string;
  label: string;
}> = [
  { key: 'caloriesKcal', id: 'nutrition-energy', label: 'Energy (kcal)' },
  { key: 'proteinGrams', id: 'nutrition-protein', label: 'Protein (grams)' },
  {
    key: 'carbohydratesGrams',
    id: 'nutrition-carbohydrates',
    label: 'Carbohydrates (grams)',
  },
  { key: 'fatGrams', id: 'nutrition-fat', label: 'Fat (grams)' },
  { key: 'fibreGrams', id: 'nutrition-fibre', label: 'Fibre (grams)' },
];

export function NutritionFields({
  value,
  disabled,
  onChange,
}: {
  value: NutritionFormValue;
  disabled: boolean;
  onChange(field: keyof NutritionFormValue, value: string): void;
}) {
  return (
    <fieldset className="record-form__fieldset">
      <legend>Nutrition measurements</legend>
      <p className="record-form__fieldset-hint">
        Enter at least one known measurement. Empty fields remain unknown.
      </p>
      <div className="record-form__grid">
        {nutritionFields.map((field) => (
          <Field
            key={field.key}
            id={field.id}
            label={field.label}
            type="number"
            min="0"
            step="any"
            value={value[field.key]}
            onChange={(event) => onChange(field.key, event.target.value)}
            disabled={disabled}
          />
        ))}
      </div>
    </fieldset>
  );
}
