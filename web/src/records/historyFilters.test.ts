import { buildRecordHistoryFilters } from './historyFilters';

describe('record history filters', () => {
  it('keeps the all-records query unfiltered when dates are blank', () => {
    expect(
      buildRecordHistoryFilters({
        recordType: 'all',
        startDate: '',
        endDate: '',
      }),
    ).toEqual({});
  });

  it('maps record type and an inclusive local date range to backend filters', () => {
    const filters = buildRecordHistoryFilters({
      recordType: 'hydration',
      startDate: '2026-08-10',
      endDate: '2026-08-12',
    });

    expect(filters.recordType).toBe('hydration');
    expect(filters.start).toMatch(/^2026-08-10T00:00:00[+-]\d{2}:\d{2}$/);
    expect(filters.end).toMatch(/^2026-08-13T00:00:00[+-]\d{2}:\d{2}$/);
  });

  it('requires paired dates and valid ordering', () => {
    expect(() =>
      buildRecordHistoryFilters({
        recordType: 'all',
        startDate: '2026-08-10',
        endDate: '',
      }),
    ).toThrow('both a start date and an end date');

    expect(() =>
      buildRecordHistoryFilters({
        recordType: 'all',
        startDate: '2026-08-12',
        endDate: '2026-08-10',
      }),
    ).toThrow('same as or later');
  });

  it('rejects impossible calendar dates', () => {
    expect(() =>
      buildRecordHistoryFilters({
        recordType: 'all',
        startDate: '2026-02-30',
        endDate: '2026-03-01',
      }),
    ).toThrow('valid start date');
  });
});
