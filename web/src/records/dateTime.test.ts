import {
  awareIsoToLocalDateTime,
  currentLocalDateTime,
  elapsedMinutes,
  localDateTimeToAwareIso,
} from './dateTime';

describe('record datetime helpers', () => {
  it('preserves local wall time and appends an explicit positive offset', () => {
    expect(localDateTimeToAwareIso('2026-08-14T21:05', -330)).toBe(
      '2026-08-14T21:05:00+05:30',
    );
  });

  it('supports a negative offset without relying on the CI timezone', () => {
    expect(localDateTimeToAwareIso('2026-01-02T06:07:08', 480)).toBe(
      '2026-01-02T06:07:08-08:00',
    );
  });

  it('converts an aware instant into a datetime-local value without losing the instant', () => {
    const local = awareIsoToLocalDateTime('2026-08-14T21:05:00+05:30', -330);
    expect(local).toBe('2026-08-14T21:05');
    expect(localDateTimeToAwareIso(local, -330)).toBe(
      '2026-08-14T21:05:00+05:30',
    );
  });

  it('rejects a naive timestamp when preparing a record for correction', () => {
    expect(() => awareIsoToLocalDateTime('2026-08-14T21:05:00')).toThrow(
      'timezone-aware',
    );
  });

  it('rejects impossible local dates and calculates local elapsed minutes', () => {
    expect(() => localDateTimeToAwareIso('2026-02-30T08:00', 0)).toThrow(
      'valid local date',
    );
    expect(elapsedMinutes('2026-08-14T22:00', '2026-08-15T06:30')).toBe(510);
  });

  it('formats a Date for a datetime-local control', () => {
    expect(currentLocalDateTime(new Date(2026, 7, 14, 9, 4))).toBe(
      '2026-08-14T09:04',
    );
  });
});
