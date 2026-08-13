import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { buildSleepRecordRequest } from '../recordRequests';
import { SleepRecordForm } from './SleepRecordForm';

describe('SleepRecordForm', () => {
  it('renders the supported sleep fields with accessible labels', () => {
    render(<SleepRecordForm isSaving={false} onSubmit={vi.fn()} />);

    expect(screen.getByLabelText('Sleep start')).toHaveAttribute(
      'type',
      'datetime-local',
    );
    expect(screen.getByLabelText('Sleep end')).toBeRequired();
    expect(screen.getByLabelText('Minutes asleep')).toBeRequired();
    expect(screen.getByLabelText('Minutes awake')).toBeRequired();
    expect(
      screen.getByLabelText('Sleep quality (optional)'),
    ).toBeInTheDocument();
  });

  it('serializes the sleep discriminator, aware period, and exact fields', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<SleepRecordForm isSaving={false} onSubmit={onSubmit} />);
    fireEvent.change(screen.getByLabelText('Sleep start'), {
      target: { value: '2026-08-14T22:00' },
    });
    fireEvent.change(screen.getByLabelText('Sleep end'), {
      target: { value: '2026-08-15T06:00' },
    });
    await userEvent.type(screen.getByLabelText('Minutes asleep'), '420');
    await userEvent.selectOptions(
      screen.getByLabelText('Sleep quality (optional)'),
      'fair',
    );
    await userEvent.type(
      screen.getByLabelText('Interruptions (optional)'),
      '2',
    );
    await userEvent.click(
      screen.getByRole('button', { name: 'Save sleep record' }),
    );

    expect(onSubmit).toHaveBeenCalledOnce();
    const request = onSubmit.mock.calls[0][0];
    expect(request).toEqual(
      expect.objectContaining({
        record_type: 'sleep',
        metadata: expect.objectContaining({ source: 'manual' }),
        data: expect.objectContaining({
          sleep_minutes: 420,
          awake_minutes: 0,
          quality: 'fair',
          stages: null,
          interruption_count: 2,
        }),
      }),
    );
    expect(request.data.period.start).toMatch(/[+-]\d{2}:\d{2}$/);
    expect(request.data.period.end).toMatch(/[+-]\d{2}:\d{2}$/);
  });

  it('rejects cross-field duration errors before transport', () => {
    expect(() =>
      buildSleepRecordRequest({
        start: '2026-08-15T06:00',
        end: '2026-08-14T22:00',
        sleepMinutes: '420',
        awakeMinutes: '0',
        quality: '',
        interruptionCount: '',
        notes: '',
      }),
    ).toThrow('Sleep end must be after sleep start');
  });

  it('preserves form input when record creation fails', async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error('server detail'));
    render(<SleepRecordForm isSaving={false} onSubmit={onSubmit} />);
    await userEvent.type(screen.getByLabelText('Minutes asleep'), '400');
    await userEvent.click(
      screen.getByRole('button', { name: 'Save sleep record' }),
    );

    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
    expect(screen.getByLabelText('Minutes asleep')).toHaveValue(400);
    expect(screen.queryByText('server detail')).not.toBeInTheDocument();
  });
});
