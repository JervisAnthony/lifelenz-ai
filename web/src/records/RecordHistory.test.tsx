import { render, screen, within } from '@testing-library/react';

import type { WellnessRecord } from '../api/types';
import { RecordHistory } from './RecordHistory';

function hydrationRecord(index: number): WellnessRecord {
  return {
    record_type: 'hydration',
    metadata: {
      record_id: `history-${index}`,
      recorded_at: `2026-08-${String(index + 10).padStart(2, '0')}T10:00:00+05:30`,
      source: 'manual',
      notes: null,
    },
    data: {
      volume_milliliters: 250 + index,
      beverage_type: 'water',
      caffeine_milligrams: null,
    },
  };
}

describe('RecordHistory', () => {
  it('shows every returned record newest first', () => {
    render(
      <RecordHistory
        records={[hydrationRecord(0), hydrationRecord(1), hydrationRecord(2)]}
      />,
    );

    expect(screen.getByRole('status')).toHaveTextContent('3 records found');
    const items = screen.getAllByRole('listitem');
    expect(items).toHaveLength(3);
    expect(within(items[0]).getByText(/^252 mL/)).toBeInTheDocument();
    expect(within(items[2]).getByText(/^250 mL/)).toBeInTheDocument();
  });

  it('renders an honest filtered empty state', () => {
    render(<RecordHistory records={[]} />);
    expect(
      screen.getByRole('heading', { name: 'No records match these filters' }),
    ).toBeInTheDocument();
  });

  it('keeps menstrual details restrained in full history', () => {
    const record: WellnessRecord = {
      record_type: 'menstrual_bleeding',
      metadata: {
        record_id: 'synthetic-menstrual-history',
        recorded_at: '2026-08-14T08:00:00+05:30',
        source: 'manual',
        notes: 'synthetic private note',
      },
      data: { flow: 'heavy', symptoms: [] },
    };

    render(<RecordHistory records={[record]} />);
    expect(
      screen.getByText('Menstrual bleeding observation'),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/heavy|synthetic private note/i),
    ).not.toBeInTheDocument();
  });
});
