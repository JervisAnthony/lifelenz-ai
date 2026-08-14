import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { buildDailyNutritionRecordRequest } from '../recordRequests';
import { DailyNutritionRecordForm } from './DailyNutritionRecordForm';

describe('DailyNutritionRecordForm', () => {
  it('builds the exact date-level nutrition payload', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<DailyNutritionRecordForm isSaving={false} onSubmit={onSubmit} />);
    fireEvent.change(screen.getByLabelText('Recorded at'), {
      target: { value: '2026-08-14T20:00' },
    });
    fireEvent.change(screen.getByLabelText('Nutrition date'), {
      target: { value: '2026-08-13' },
    });
    await userEvent.type(screen.getByLabelText('Meal count (optional)'), '3');
    await userEvent.type(screen.getByLabelText('Protein (grams)'), '24');
    await userEvent.click(
      screen.getByRole('button', { name: 'Save daily nutrition record' }),
    );

    expect(onSubmit).toHaveBeenCalledWith({
      record_type: 'daily_nutrition',
      metadata: {
        recorded_at: expect.stringMatching(/[+-]\d{2}:\d{2}$/),
        source: 'manual',
        notes: null,
      },
      data: {
        nutrition_date: '2026-08-13',
        meal_count: 3,
        nutrition: {
          calories_kcal: null,
          protein_grams: 24,
          carbohydrates_grams: null,
          fat_grams: null,
          fibre_grams: null,
        },
      },
    });
  });

  it('preserves zero and maps empty optional fields to null', () => {
    const request = buildDailyNutritionRecordRequest({
      recordedAt: '2026-08-14T20:00',
      nutritionDate: '2026-08-14',
      mealCount: '0',
      nutrition: {
        caloriesKcal: '0',
        proteinGrams: '',
        carbohydratesGrams: '',
        fatGrams: '',
        fibreGrams: '',
      },
      notes: '',
    });
    expect(request.data.meal_count).toBe(0);
    expect(request.data.nutrition).toEqual({
      calories_kcal: 0,
      protein_grams: null,
      carbohydrates_grams: null,
      fat_grams: null,
      fibre_grams: null,
    });
  });

  it('rejects invalid dates, meal counts, and measurements', () => {
    const base = {
      recordedAt: '2026-08-14T20:00',
      nutritionDate: '2026-08-14',
      mealCount: '',
      nutrition: {
        caloriesKcal: '200',
        proteinGrams: '',
        carbohydratesGrams: '',
        fatGrams: '',
        fibreGrams: '',
      },
      notes: '',
    };
    expect(() =>
      buildDailyNutritionRecordRequest({
        ...base,
        nutritionDate: '2026-02-30',
      }),
    ).toThrow('valid nutrition date');
    expect(() =>
      buildDailyNutritionRecordRequest({ ...base, mealCount: '1.5' }),
    ).toThrow('whole number');
    expect(() =>
      buildDailyNutritionRecordRequest({
        ...base,
        nutrition: { ...base.nutrition, caloriesKcal: '-1' },
      }),
    ).toThrow('Energy cannot be negative');
  });

  it('preserves input after failure and disables a pending save', async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error('offline'));
    const { rerender } = render(
      <DailyNutritionRecordForm isSaving={false} onSubmit={onSubmit} />,
    );
    await userEvent.type(screen.getByLabelText('Protein (grams)'), '24');
    await userEvent.click(
      screen.getByRole('button', { name: 'Save daily nutrition record' }),
    );
    expect(await screen.findByLabelText('Protein (grams)')).toHaveValue(24);
    rerender(<DailyNutritionRecordForm isSaving onSubmit={onSubmit} />);
    expect(screen.getByRole('button', { name: 'Saving…' })).toBeDisabled();
  });
});
