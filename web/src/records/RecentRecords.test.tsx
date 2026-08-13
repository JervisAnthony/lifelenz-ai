import { render, screen, within } from '@testing-library/react';

import type { WellnessRecord } from '../api/types';
import { RecentRecords } from './RecentRecords';
import { presentRecord } from './recordPresentation';
import { recordTypeLabels } from './recordTypes';

function hydrationRecord(index: number): WellnessRecord {
  return {
    record_type: 'hydration',
    metadata: {
      record_id: `record-${index}`,
      recorded_at: `2026-08-${String(index + 1).padStart(2, '0')}T10:00:00+05:30`,
      source: 'manual',
      notes: null,
    },
    data: {
      volume_milliliters: 100 + index,
      beverage_type: 'water',
      caffeine_milligrams: null,
    },
  };
}

describe('recent record presentation', () => {
  it('preserves server chronology while limiting the list to its newest ten', () => {
    render(
      <RecentRecords
        records={Array.from({ length: 12 }, (_, index) =>
          hydrationRecord(index),
        )}
      />,
    );

    const items = screen.getAllByRole('listitem');
    expect(items).toHaveLength(10);
    expect(within(items[0]).getByText(/^102 mL/)).toBeInTheDocument();
    expect(within(items[9]).getByText(/^111 mL/)).toBeInTheDocument();
    expect(screen.queryByText(/^100 mL/)).not.toBeInTheDocument();
  });

  it('keeps subjective and menstrual summaries restrained', () => {
    const checkIn: WellnessRecord = {
      record_type: 'subjective_check_in',
      metadata: {
        record_id: 'check-in-record',
        recorded_at: '2026-08-14T20:00:00+05:30',
        source: 'manual',
        notes: 'private note',
      },
      data: {
        mood_score: 2,
        energy_score: 4,
        stress_score: 8,
        motivation_score: null,
        mood_category: 'low',
        tags: ['tense'],
      },
    };
    const menstrual: WellnessRecord = {
      record_type: 'menstrual_bleeding',
      metadata: {
        record_id: 'menstrual-record',
        recorded_at: '2026-08-14T08:00:00+05:30',
        source: 'manual',
        notes: 'private note',
      },
      data: { flow: 'heavy', symptoms: [] },
    };

    expect(presentRecord(checkIn).summary).toBe(
      'Private self-reported scores recorded',
    );
    expect(presentRecord(checkIn).summary).not.toMatch(/2|4|8|low|tense/);
    expect(presentRecord(menstrual).label).toBe(
      'Menstrual bleeding observation',
    );
    expect(presentRecord(menstrual).summary).not.toMatch(/heavy|private note/);
  });

  it('defines a friendly exhaustive label set for all ten API types', () => {
    expect(recordTypeLabels).toEqual({
      sleep: 'Sleep',
      daily_activity: 'Daily activity',
      workout: 'Workout',
      hydration: 'Hydration',
      meal: 'Meal',
      daily_nutrition: 'Daily nutrition',
      body_measurement: 'Body measurement',
      subjective_check_in: 'Wellness check-in',
      menstrual_bleeding: 'Menstrual bleeding observation',
      menstrual_cycle: 'Menstrual cycle',
    });
  });
});
