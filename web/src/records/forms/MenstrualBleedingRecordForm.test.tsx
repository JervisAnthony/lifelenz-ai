import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { buildMenstrualBleedingRecordRequest } from '../recordRequests';
import { MenstrualBleedingRecordForm } from './MenstrualBleedingRecordForm';

describe('MenstrualBleedingRecordForm', () => {
  it('offers every flow and symptom option with friendly labels', () => {
    render(<MenstrualBleedingRecordForm isSaving={false} onSubmit={vi.fn()} />);
    const flow = screen.getByLabelText<HTMLSelectElement>('Flow description');
    expect(
      Array.from(flow.options, (option) => [option.value, option.text]),
    ).toEqual([
      ['', 'Choose a flow description'],
      ['spotting', 'Spotting'],
      ['light', 'Light'],
      ['moderate', 'Moderate'],
      ['heavy', 'Heavy'],
    ]);
    const symptomLabels = [
      'Cramps',
      'Bloating',
      'Headache',
      'Back discomfort',
      'Breast tenderness',
      'Fatigue',
      'Mood change',
      'Nausea',
      'Acne',
      'Food craving',
      'Sleep change',
      'Other',
    ];
    expect(
      symptomLabels.map((label) => screen.getByLabelText(label)),
    ).toHaveLength(12);
    expect(screen.getByLabelText('Back discomfort')).toBeInTheDocument();
    expect(screen.getByLabelText('Breast tenderness')).toBeInTheDocument();
    expect(screen.getByLabelText('Food craving')).toBeInTheDocument();
    expect(screen.queryByText('back_discomfort')).not.toBeInTheDocument();
  });

  it('builds the exact ordered symptom payload with nullable intensity', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(
      <MenstrualBleedingRecordForm isSaving={false} onSubmit={onSubmit} />,
    );
    fireEvent.change(screen.getByLabelText('Recorded at'), {
      target: { value: '2026-08-14T09:00' },
    });
    await userEvent.selectOptions(
      screen.getByLabelText('Flow description'),
      'moderate',
    );
    await userEvent.click(screen.getByLabelText('Cramps'));
    await userEvent.selectOptions(
      screen.getByLabelText('Intensity for cramps (optional)'),
      'strong',
    );
    await userEvent.click(screen.getByLabelText('Fatigue'));
    await userEvent.click(
      screen.getByRole('button', { name: 'Save bleeding observation' }),
    );

    expect(onSubmit).toHaveBeenCalledWith({
      record_type: 'menstrual_bleeding',
      metadata: {
        recorded_at: expect.stringMatching(/[+-]\d{2}:\d{2}$/),
        source: 'manual',
        notes: null,
      },
      data: {
        flow: 'moderate',
        symptoms: [
          { symptom: 'cramps', intensity: 'strong' },
          { symptom: 'fatigue', intensity: null },
        ],
      },
    });
  });

  it('requires flow and rejects duplicate symptom types', () => {
    const base = {
      recordedAt: '2026-08-14T09:00',
      flow: 'light' as const,
      symptoms: [{ symptom: 'cramps' as const, intensity: '' as const }],
      notes: '',
    };
    expect(() =>
      buildMenstrualBleedingRecordRequest({ ...base, flow: '' }),
    ).toThrow('Choose a flow description');
    expect(() =>
      buildMenstrualBleedingRecordRequest({
        ...base,
        symptoms: [...base.symptoms, ...base.symptoms],
      }),
    ).toThrow('recorded once');
  });

  it('preserves selections after failure and disables a pending save', async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error('offline'));
    const { rerender } = render(
      <MenstrualBleedingRecordForm isSaving={false} onSubmit={onSubmit} />,
    );
    await userEvent.selectOptions(
      screen.getByLabelText('Flow description'),
      'light',
    );
    await userEvent.click(screen.getByLabelText('Headache'));
    await userEvent.click(
      screen.getByRole('button', { name: 'Save bleeding observation' }),
    );
    expect(await screen.findByLabelText('Flow description')).toHaveValue(
      'light',
    );
    expect(screen.getByLabelText('Headache')).toBeChecked();
    expect(
      screen.getByText(/without showing its details/i),
    ).toBeInTheDocument();
    rerender(<MenstrualBleedingRecordForm isSaving onSubmit={onSubmit} />);
    expect(screen.getByRole('button', { name: 'Saving…' })).toBeDisabled();
  });
});
