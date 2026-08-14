import { fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { buildWorkoutRecordRequest } from '../recordRequests';
import { WorkoutRecordForm } from './WorkoutRecordForm';

describe('WorkoutRecordForm', () => {
  it('presents every backend workout enum with a friendly label', () => {
    render(<WorkoutRecordForm isSaving={false} onSubmit={vi.fn()} />);
    const select = screen.getByLabelText('Workout type');

    expect(within(select).getAllByRole('option')).toHaveLength(11);
    expect(
      Array.from((select as HTMLSelectElement).options).map(
        (option) => option.value,
      ),
    ).toEqual([
      'walking',
      'running',
      'cycling',
      'swimming',
      'strength_training',
      'yoga',
      'hiking',
      'rowing',
      'elliptical',
      'sport',
      'other',
    ]);
    expect(
      within(select).getByRole('option', { name: 'Strength training' }),
    ).toHaveValue('strength_training');
  });

  it('builds aware timing and the exact optional-measurement payload', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<WorkoutRecordForm isSaving={false} onSubmit={onSubmit} />);
    fireEvent.change(screen.getByLabelText('Workout start'), {
      target: { value: '2026-08-14T06:30' },
    });
    fireEvent.change(screen.getByLabelText('Workout end'), {
      target: { value: '2026-08-14T07:45' },
    });
    await userEvent.selectOptions(
      screen.getByLabelText('Workout type'),
      'strength_training',
    );
    await userEvent.type(screen.getByLabelText('Distance (kilometers)'), '2.4');
    await userEvent.type(
      screen.getByLabelText('Active calories (kcal)'),
      '225.5',
    );
    await userEvent.type(
      screen.getByLabelText('Perceived exertion (1–10)'),
      '6',
    );
    await userEvent.type(
      screen.getByLabelText('Average heart rate (bpm)'),
      '118.5',
    );
    await userEvent.click(
      screen.getByRole('button', { name: 'Save workout record' }),
    );

    expect(onSubmit).toHaveBeenCalledOnce();
    expect(onSubmit.mock.calls[0][0]).toEqual({
      record_type: 'workout',
      metadata: {
        recorded_at: expect.stringMatching(
          /^2026-08-14T07:45:00[+-]\d{2}:\d{2}$/,
        ),
        source: 'manual',
        notes: null,
      },
      data: {
        period: {
          start: expect.stringMatching(/^2026-08-14T06:30:00[+-]\d{2}:\d{2}$/),
          end: expect.stringMatching(/^2026-08-14T07:45:00[+-]\d{2}:\d{2}$/),
        },
        workout_type: 'strength_training',
        distance_kilometers: 2.4,
        active_calories_kcal: 225.5,
        perceived_exertion: 6,
        average_heart_rate_bpm: 118.5,
      },
    });
  });

  it('keeps empty optional fields null and validates timing and numbers', () => {
    const base = {
      start: '2026-08-14T06:30',
      end: '2026-08-14T07:30',
      workoutType: 'walking' as const,
      distanceKilometers: '',
      activeCaloriesKcal: '',
      perceivedExertion: '',
      averageHeartRateBpm: '',
      notes: '',
    };
    expect(buildWorkoutRecordRequest(base).data).toEqual(
      expect.objectContaining({
        distance_kilometers: null,
        active_calories_kcal: null,
        perceived_exertion: null,
        average_heart_rate_bpm: null,
      }),
    );
    expect(() =>
      buildWorkoutRecordRequest({ ...base, end: base.start }),
    ).toThrow('after workout start');
    expect(() =>
      buildWorkoutRecordRequest({ ...base, perceivedExertion: '5.5' }),
    ).toThrow('whole number');
    expect(() =>
      buildWorkoutRecordRequest({ ...base, averageHeartRateBpm: '0' }),
    ).toThrow('greater than zero');
  });

  it('preserves values after failure and disables duplicate submission while saving', async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error('offline'));
    const { rerender } = render(
      <WorkoutRecordForm isSaving={false} onSubmit={onSubmit} />,
    );
    await userEvent.type(screen.getByLabelText('Distance (kilometers)'), '7.5');
    await userEvent.click(
      screen.getByRole('button', { name: 'Save workout record' }),
    );
    expect(await screen.findByLabelText('Distance (kilometers)')).toHaveValue(
      7.5,
    );

    rerender(<WorkoutRecordForm isSaving onSubmit={onSubmit} />);
    expect(screen.getByRole('button', { name: 'Saving…' })).toBeDisabled();
  });
});
