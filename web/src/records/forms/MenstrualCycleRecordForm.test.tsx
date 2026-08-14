import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { buildMenstrualCycleRecordRequest } from '../recordRequests';
import { MenstrualCycleRecordForm } from './MenstrualCycleRecordForm';

describe('MenstrualCycleRecordForm', () => {
  it('builds an open cycle with a null end date', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<MenstrualCycleRecordForm isSaving={false} onSubmit={onSubmit} />);
    fireEvent.change(screen.getByLabelText('Recorded at'), {
      target: { value: '2026-08-14T09:00' },
    });
    fireEvent.change(screen.getByLabelText('Cycle start date'), {
      target: { value: '2026-08-12' },
    });
    await userEvent.click(
      screen.getByRole('button', { name: 'Save menstrual cycle' }),
    );

    expect(onSubmit).toHaveBeenCalledWith({
      record_type: 'menstrual_cycle',
      metadata: {
        recorded_at: expect.stringMatching(/[+-]\d{2}:\d{2}$/),
        source: 'manual',
        notes: null,
      },
      data: { start_date: '2026-08-12', end_date: null },
    });
  });

  it('accepts an end date equal to or after the start date', () => {
    const base = {
      recordedAt: '2026-08-14T09:00',
      startDate: '2026-08-12',
      endDate: '2026-08-12',
      notes: '',
    };
    expect(buildMenstrualCycleRecordRequest(base).data.end_date).toBe(
      '2026-08-12',
    );
    expect(
      buildMenstrualCycleRecordRequest({ ...base, endDate: '2026-08-15' }).data
        .end_date,
    ).toBe('2026-08-15');
  });

  it('rejects incomplete, impossible, and reversed dates', () => {
    const base = {
      recordedAt: '2026-08-14T09:00',
      startDate: '2026-08-12',
      endDate: '',
      notes: '',
    };
    expect(() =>
      buildMenstrualCycleRecordRequest({ ...base, startDate: '' }),
    ).toThrow('complete cycle start date');
    expect(() =>
      buildMenstrualCycleRecordRequest({ ...base, startDate: '2026-02-30' }),
    ).toThrow('valid cycle start date');
    expect(() =>
      buildMenstrualCycleRecordRequest({ ...base, endDate: '2026-08-11' }),
    ).toThrow('cannot be before');
  });

  it('preserves dates after failure and disables a pending save', async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error('offline'));
    const { rerender } = render(
      <MenstrualCycleRecordForm isSaving={false} onSubmit={onSubmit} />,
    );
    fireEvent.change(screen.getByLabelText('Cycle end date (optional)'), {
      target: { value: '2026-08-18' },
    });
    await userEvent.click(
      screen.getByRole('button', { name: 'Save menstrual cycle' }),
    );
    expect(
      await screen.findByLabelText('Cycle end date (optional)'),
    ).toHaveValue('2026-08-18');
    expect(
      screen.getByText(/without prediction or classification/i),
    ).toBeInTheDocument();
    rerender(<MenstrualCycleRecordForm isSaving onSubmit={onSubmit} />);
    expect(screen.getByRole('button', { name: 'Saving…' })).toBeDisabled();
  });
});
