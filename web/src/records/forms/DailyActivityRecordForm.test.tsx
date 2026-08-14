import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { buildDailyActivityRecordRequest } from '../recordRequests';
import { DailyActivityRecordForm } from './DailyActivityRecordForm';

describe('DailyActivityRecordForm', () => {
  it('renders the supported daily totals and builds the exact canonical payload', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<DailyActivityRecordForm isSaving={false} onSubmit={onSubmit} />);
    fireEvent.change(screen.getByLabelText('Recorded at'), {
      target: { value: '2026-08-14T20:15' },
    });
    fireEvent.change(screen.getByLabelText('Activity date'), {
      target: { value: '2026-08-14' },
    });
    await userEvent.type(screen.getByLabelText('Steps'), '4200');
    await userEvent.type(
      screen.getByLabelText('Distance (kilometers)'),
      '3.25',
    );
    await userEvent.type(screen.getByLabelText('Active minutes'), '42.5');
    await userEvent.type(
      screen.getByLabelText('Active calories (kcal)'),
      '180.5',
    );
    await userEvent.click(
      screen.getByRole('button', { name: 'Save daily activity record' }),
    );

    expect(onSubmit).toHaveBeenCalledOnce();
    expect(onSubmit.mock.calls[0][0]).toEqual({
      record_type: 'daily_activity',
      metadata: {
        recorded_at: expect.stringMatching(/[+-]\d{2}:\d{2}$/),
        source: 'manual',
        notes: null,
      },
      data: {
        activity_date: '2026-08-14',
        steps: 4200,
        distance_kilometers: 3.25,
        active_minutes: 42.5,
        active_calories_kcal: 180.5,
      },
    });
  });

  it('omits empty optional totals instead of converting them to zero', () => {
    const request = buildDailyActivityRecordRequest({
      recordedAt: '2026-08-14T20:15',
      activityDate: '2026-08-14',
      steps: '',
      distanceKilometers: '',
      activeMinutes: '',
      activeCaloriesKcal: '',
      notes: '',
    });

    expect(request.data).toEqual({ activity_date: '2026-08-14' });
  });

  it('rejects incomplete dates, fractional steps, and negative totals', () => {
    const base = {
      recordedAt: '2026-08-14T20:15',
      activityDate: '2026-08-14',
      steps: '',
      distanceKilometers: '',
      activeMinutes: '',
      activeCaloriesKcal: '',
      notes: '',
    };
    expect(() =>
      buildDailyActivityRecordRequest({ ...base, activityDate: '' }),
    ).toThrow('complete activity date');
    expect(() =>
      buildDailyActivityRecordRequest({ ...base, steps: '2.5' }),
    ).toThrow('whole number');
    expect(() =>
      buildDailyActivityRecordRequest({ ...base, activeMinutes: '-1' }),
    ).toThrow('Active minutes cannot be negative');
  });

  it('preserves entered totals after a failed save', async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error('offline'));
    render(<DailyActivityRecordForm isSaving={false} onSubmit={onSubmit} />);
    await userEvent.type(screen.getByLabelText('Steps'), '5100');
    await userEvent.click(
      screen.getByRole('button', { name: 'Save daily activity record' }),
    );

    expect(await screen.findByLabelText('Steps')).toHaveValue(5100);
    expect(onSubmit).toHaveBeenCalledOnce();
  });

  it('disables saving while a request is pending', () => {
    render(<DailyActivityRecordForm isSaving onSubmit={vi.fn()} />);
    expect(screen.getByRole('button', { name: 'Saving…' })).toBeDisabled();
  });
});
