import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { buildSubjectiveCheckInRequest } from '../recordRequests';
import { SubjectiveCheckInForm } from './SubjectiveCheckInForm';

describe('SubjectiveCheckInForm', () => {
  it('maps required 1–10 scales, optional context, and neutral tags', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<SubjectiveCheckInForm isSaving={false} onSubmit={onSubmit} />);
    fireEvent.change(screen.getByLabelText('Recorded at'), {
      target: { value: '2026-08-14T20:15' },
    });
    await userEvent.selectOptions(screen.getByLabelText('Mood score'), '6');
    await userEvent.selectOptions(screen.getByLabelText('Energy score'), '7');
    await userEvent.selectOptions(screen.getByLabelText('Stress score'), '3');
    await userEvent.selectOptions(
      screen.getByLabelText('Motivation score (optional)'),
      '5',
    );
    await userEvent.selectOptions(
      screen.getByLabelText('Mood description (optional)'),
      'neutral',
    );
    await userEvent.click(screen.getByLabelText('Calm'));
    await userEvent.click(
      screen.getByRole('button', { name: 'Save wellness check-in' }),
    );

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        record_type: 'subjective_check_in',
        data: {
          mood_score: 6,
          energy_score: 7,
          stress_score: 3,
          motivation_score: 5,
          mood_category: 'neutral',
          tags: ['calm'],
        },
      }),
    );
    expect(screen.getByText(/not medical assessments/i)).toBeInTheDocument();
  });

  it('requires each core score in the serializer', () => {
    expect(() =>
      buildSubjectiveCheckInRequest({
        recordedAt: '2026-08-14T20:15',
        mood: '',
        energy: '5',
        stress: '5',
        motivation: '',
        moodCategory: '',
        tags: [],
        notes: '',
      }),
    ).toThrow('mood score from 1 through 10');
  });

  it('renders exact scale bounds and required semantics', () => {
    render(<SubjectiveCheckInForm isSaving={false} onSubmit={vi.fn()} />);
    expect(screen.getByLabelText('Mood score')).toBeRequired();
    expect(screen.getAllByRole('option', { name: '10' })).toHaveLength(4);
    expect(
      screen.queryByText(/healthy|unhealthy|dangerous/i),
    ).not.toBeInTheDocument();
  });
});
