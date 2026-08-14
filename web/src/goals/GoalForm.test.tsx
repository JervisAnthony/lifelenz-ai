import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import type { WellnessGoalRequest } from '../api/types';
import { GoalForm } from './GoalForm';
import { buildGoalRequest } from './goalRequests';

describe('GoalForm', () => {
  it('offers every backend metric with a friendly label and canonical unit', async () => {
    render(
      <GoalForm
        mode="create"
        isSaving={false}
        onSubmit={vi.fn().mockResolvedValue(undefined)}
      />,
    );
    const metric = screen.getByLabelText<HTMLSelectElement>('Metric');
    expect(metric.options).toHaveLength(21);
    expect(Array.from(metric.options, (option) => option.value)).toEqual([
      'sleep_duration',
      'time_in_bed',
      'sleep_efficiency',
      'steps',
      'distance',
      'active_minutes',
      'active_calories',
      'water_intake',
      'calories',
      'protein',
      'carbohydrates',
      'fat',
      'fibre',
      'weight',
      'height',
      'bmi',
      'body_fat',
      'mood_score',
      'energy_score',
      'stress_score',
      'recovery_score',
    ]);
    expect(
      Array.from(metric.options).every(
        (option) => !option.text.includes('_') && option.text.length > 0,
      ),
    ).toBe(true);
    await userEvent.selectOptions(metric, 'water_intake');
    expect(screen.getByText('milliliters')).toBeInTheDocument();
    await userEvent.selectOptions(metric, 'bmi');
    expect(screen.getByText('kg/m²')).toBeInTheDocument();
  });

  it('builds the exact complete create request with trimmed optional text', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<GoalForm mode="create" isSaving={false} onSubmit={onSubmit} />);
    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText('Metric'), 'distance');
    await user.type(screen.getByLabelText('Target value'), '12.34');
    await user.selectOptions(screen.getByLabelText('Direction'), 'maintain');
    await user.selectOptions(screen.getByLabelText('Status'), 'active');
    fireEvent.change(screen.getByLabelText('Start date (optional)'), {
      target: { value: '2026-08-01' },
    });
    fireEvent.change(screen.getByLabelText('Target date (optional)'), {
      target: { value: '2026-09-01' },
    });
    await user.type(screen.getByLabelText('Title (optional)'), '  Walking  ');
    await user.type(
      screen.getByLabelText('Description (optional)'),
      '  Synthetic description  ',
    );
    await user.click(screen.getByRole('button', { name: 'Create goal' }));

    expect(onSubmit).toHaveBeenCalledWith({
      target: { metric: 'distance', value: 12.34, unit: 'kilometers' },
      direction: 'maintain',
      status: 'active',
      start_date: '2026-08-01',
      target_date: '2026-09-01',
      title: 'Walking',
      description: 'Synthetic description',
    });
  });

  it('preserves explicit zero and rejects invalid targets and dates', () => {
    const base = {
      metric: 'steps' as const,
      targetValue: '0',
      direction: 'exactly' as const,
      status: 'draft' as const,
      startDate: '',
      targetDate: '',
      title: '',
      description: '',
    };
    expect(buildGoalRequest(base).target).toEqual({
      metric: 'steps',
      value: 0,
      unit: 'count',
    });
    expect(() => buildGoalRequest({ ...base, targetValue: '' })).toThrow(
      'finite number',
    );
    expect(() => buildGoalRequest({ ...base, targetValue: '-1' })).toThrow(
      'finite number',
    );
    expect(() =>
      buildGoalRequest({
        ...base,
        startDate: '2026-08-02',
        targetDate: '2026-08-01',
      }),
    ).toThrow('cannot be before');
    expect(() =>
      buildGoalRequest({ ...base, startDate: '2026-02-30' }),
    ).toThrow('valid start date');
  });

  it('renders all statuses and directions and preserves edit input on failure', async () => {
    const initialValue: WellnessGoalRequest = {
      target: { metric: 'steps', value: 1234, unit: 'count' },
      direction: 'increase',
      status: 'paused',
      start_date: null,
      target_date: null,
      title: 'Synthetic target',
      description: null,
    };
    const onSubmit = vi.fn().mockRejectedValue(new Error('offline'));
    render(
      <GoalForm
        mode="edit"
        initialValue={initialValue}
        isSaving={false}
        error="The update was not saved."
        onSubmit={onSubmit}
        onCancel={vi.fn()}
      />,
    );
    expect(
      Array.from(
        screen.getByLabelText<HTMLSelectElement>('Direction').options,
        (option) => option.value,
      ),
    ).toEqual([
      'at_least',
      'at_most',
      'exactly',
      'increase',
      'decrease',
      'maintain',
    ]);
    expect(
      Array.from(
        screen.getByLabelText<HTMLSelectElement>('Status').options,
        (option) => option.value,
      ),
    ).toEqual(['draft', 'active', 'paused', 'completed', 'cancelled']);
    const target = screen.getByLabelText('Target value');
    await userEvent.clear(target);
    await userEvent.type(target, '2345');
    await userEvent.click(
      screen.getByRole('button', { name: 'Save goal changes' }),
    );
    expect(await screen.findByLabelText('Target value')).toHaveValue(2345);
    expect(screen.getByText('The update was not saved.')).toBeInTheDocument();
  });

  it('disables submit and cancel controls while pending', () => {
    render(
      <GoalForm
        mode="edit"
        initialValue={{
          target: { metric: 'steps', value: 1, unit: 'count' },
          direction: 'at_least',
          status: 'draft',
          start_date: null,
          target_date: null,
          title: null,
          description: null,
        }}
        isSaving
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByRole('button', { name: 'Saving…' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Cancel edit' })).toBeDisabled();
  });
});
