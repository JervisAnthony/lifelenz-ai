import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { buildBodyMeasurementRecordRequest } from '../recordRequests';
import { BodyMeasurementRecordForm } from './BodyMeasurementRecordForm';

describe('BodyMeasurementRecordForm', () => {
  it('renders canonical units and builds the exact neutral payload', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<BodyMeasurementRecordForm isSaving={false} onSubmit={onSubmit} />);
    fireEvent.change(screen.getByLabelText('Recorded at'), {
      target: { value: '2026-08-14T08:00' },
    });
    await userEvent.type(screen.getByLabelText('Weight (kilograms)'), '72.4');
    await userEvent.type(
      screen.getByLabelText('Height (meters, optional)'),
      '1.78',
    );
    await userEvent.type(
      screen.getByLabelText('Body fat (percent, optional)'),
      '21.5',
    );
    await userEvent.type(
      screen.getByLabelText('Waist circumference (centimeters, optional)'),
      '81.2',
    );
    await userEvent.click(
      screen.getByRole('button', { name: 'Save body measurement' }),
    );

    expect(onSubmit).toHaveBeenCalledOnce();
    expect(onSubmit.mock.calls[0][0]).toEqual({
      record_type: 'body_measurement',
      metadata: {
        recorded_at: expect.stringMatching(/[+-]\d{2}:\d{2}$/),
        source: 'manual',
        notes: null,
      },
      data: {
        weight_kilograms: 72.4,
        height_meters: 1.78,
        body_fat_percent: 21.5,
        waist_circumference_centimeters: 81.2,
      },
    });
  });

  it('sends empty optional measurements as null', () => {
    expect(
      buildBodyMeasurementRecordRequest({
        recordedAt: '2026-08-14T08:00',
        weightKilograms: '72.4',
        heightMeters: '',
        bodyFatPercent: '',
        waistCircumferenceCentimeters: '',
        notes: '',
      }).data,
    ).toEqual({
      weight_kilograms: 72.4,
      height_meters: null,
      body_fat_percent: null,
      waist_circumference_centimeters: null,
    });
  });

  it('validates required weight and optional backend ranges', () => {
    const base = {
      recordedAt: '2026-08-14T08:00',
      weightKilograms: '72.4',
      heightMeters: '',
      bodyFatPercent: '',
      waistCircumferenceCentimeters: '',
      notes: '',
    };
    expect(() =>
      buildBodyMeasurementRecordRequest({ ...base, weightKilograms: '' }),
    ).toThrow('Weight must be greater');
    expect(() =>
      buildBodyMeasurementRecordRequest({ ...base, heightMeters: '-1' }),
    ).toThrow('Height must be greater');
    expect(() =>
      buildBodyMeasurementRecordRequest({ ...base, bodyFatPercent: '100.1' }),
    ).toThrow('cannot exceed 100');
  });

  it('preserves a rejected value and uses non-judgmental copy', async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error('offline'));
    render(<BodyMeasurementRecordForm isSaving={false} onSubmit={onSubmit} />);
    await userEvent.type(screen.getByLabelText('Weight (kilograms)'), '68.2');
    await userEvent.click(
      screen.getByRole('button', { name: 'Save body measurement' }),
    );

    expect(await screen.findByLabelText('Weight (kilograms)')).toHaveValue(
      68.2,
    );
    expect(
      screen.getByText(/without classification or interpretation/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/healthy|ideal|normal|target/i)).toBeNull();
  });

  it('disables saving while a request is pending', () => {
    render(<BodyMeasurementRecordForm isSaving onSubmit={vi.fn()} />);
    expect(screen.getByRole('button', { name: 'Saving…' })).toBeDisabled();
  });
});
