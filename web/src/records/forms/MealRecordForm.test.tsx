import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { buildMealRecordRequest } from '../recordRequests';
import { MealRecordForm } from './MealRecordForm';

describe('MealRecordForm', () => {
  it('renders every meal type and builds the exact nested nutrition payload', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<MealRecordForm isSaving={false} onSubmit={onSubmit} />);
    const mealType = screen.getByLabelText<HTMLSelectElement>('Meal type');
    expect(
      Array.from(mealType.options, (option) => [option.value, option.text]),
    ).toEqual([
      ['', 'Choose a meal type'],
      ['breakfast', 'Breakfast'],
      ['lunch', 'Lunch'],
      ['dinner', 'Dinner'],
      ['snack', 'Snack'],
      ['other', 'Other'],
    ]);
    fireEvent.change(screen.getByLabelText('Recorded at'), {
      target: { value: '2026-08-14T12:30' },
    });
    await userEvent.selectOptions(screen.getByLabelText('Meal type'), 'lunch');
    await userEvent.type(
      screen.getByLabelText('Meal name (optional)'),
      '  Rice and vegetables  ',
    );
    await userEvent.type(screen.getByLabelText('Energy (kcal)'), '420');
    await userEvent.type(screen.getByLabelText('Protein (grams)'), '18.5');
    await userEvent.click(
      screen.getByRole('button', { name: 'Save meal record' }),
    );

    expect(onSubmit).toHaveBeenCalledWith({
      record_type: 'meal',
      metadata: {
        recorded_at: expect.stringMatching(/[+-]\d{2}:\d{2}$/),
        source: 'manual',
        notes: null,
      },
      data: {
        meal_type: 'lunch',
        name: 'Rice and vegetables',
        nutrition: {
          calories_kcal: 420,
          protein_grams: 18.5,
          carbohydrates_grams: null,
          fat_grams: null,
          fibre_grams: null,
        },
      },
    });
  });

  it('requires a meal type and at least one non-negative measurement', () => {
    const base = {
      recordedAt: '2026-08-14T12:30',
      mealType: 'lunch' as const,
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
    expect(() => buildMealRecordRequest({ ...base, mealType: '' })).toThrow(
      'Choose a meal type',
    );
    expect(() => buildMealRecordRequest(base)).toThrow(
      'at least one nutrition measurement',
    );
    expect(() =>
      buildMealRecordRequest({
        ...base,
        nutrition: { ...base.nutrition, fatGrams: '-1' },
      }),
    ).toThrow('Fat cannot be negative');
  });

  it('preserves entered data after a failed save', async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error('offline'));
    render(<MealRecordForm isSaving={false} onSubmit={onSubmit} />);
    await userEvent.selectOptions(screen.getByLabelText('Meal type'), 'snack');
    await userEvent.type(screen.getByLabelText('Energy (kcal)'), '120');
    await userEvent.click(
      screen.getByRole('button', { name: 'Save meal record' }),
    );
    expect(await screen.findByLabelText('Meal type')).toHaveValue('snack');
    expect(screen.getByLabelText('Energy (kcal)')).toHaveValue(120);
  });

  it('disables saving while a request is pending', () => {
    render(<MealRecordForm isSaving onSubmit={vi.fn()} />);
    expect(screen.getByRole('button', { name: 'Saving…' })).toBeDisabled();
  });
});
