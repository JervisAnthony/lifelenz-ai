import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { buildHydrationRecordRequest } from '../recordRequests';
import { HydrationRecordForm } from './HydrationRecordForm';

describe('HydrationRecordForm', () => {
  it('builds the canonical milliliter payload and aware timestamp', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<HydrationRecordForm isSaving={false} onSubmit={onSubmit} />);
    fireEvent.change(screen.getByLabelText('Recorded at'), {
      target: { value: '2026-08-14T10:30' },
    });
    await userEvent.type(screen.getByLabelText('Volume (milliliters)'), '350');
    await userEvent.selectOptions(screen.getByLabelText('Beverage'), 'tea');
    await userEvent.type(
      screen.getByLabelText('Caffeine in milligrams (optional)'),
      '20',
    );
    await userEvent.click(
      screen.getByRole('button', { name: 'Save hydration record' }),
    );

    expect(onSubmit).toHaveBeenCalledOnce();
    expect(onSubmit.mock.calls[0][0]).toEqual({
      record_type: 'hydration',
      metadata: {
        recorded_at: expect.stringMatching(/[+-]\d{2}:\d{2}$/),
        source: 'manual',
        notes: null,
      },
      data: {
        volume_milliliters: 350,
        beverage_type: 'tea',
        caffeine_milligrams: 20,
      },
    });
  });

  it('rejects non-positive volume and negative optional caffeine', () => {
    const base = {
      recordedAt: '2026-08-14T10:30',
      volume: '0',
      beverageType: 'water' as const,
      caffeine: '',
      notes: '',
    };
    expect(() => buildHydrationRecordRequest(base)).toThrow(
      'volume greater than zero',
    );
    expect(() =>
      buildHydrationRecordRequest({ ...base, volume: '250', caffeine: '-1' }),
    ).toThrow('Caffeine cannot be negative');
  });

  it('uses textual saving state and disables duplicate submission', () => {
    render(<HydrationRecordForm isSaving onSubmit={vi.fn()} />);
    expect(screen.getByRole('button', { name: 'Saving…' })).toBeDisabled();
  });
});
