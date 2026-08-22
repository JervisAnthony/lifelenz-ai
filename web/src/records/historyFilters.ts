import type { WellnessRecordListFilters } from '../api/records';
import type { WellnessRecordType } from '../api/types';
import { localDateTimeToAwareIso } from './dateTime';

const DATE_PATTERN = /^(\d{4})-(\d{2})-(\d{2})$/;

function parsedLocalDate(value: string, fieldLabel: string): Date {
  const match = DATE_PATTERN.exec(value);
  if (!match) {
    throw new Error(`Enter a valid ${fieldLabel}.`);
  }
  const [, year, month, day] = match;
  const date = new Date(Number(year), Number(month) - 1, Number(day));
  if (
    date.getFullYear() !== Number(year) ||
    date.getMonth() !== Number(month) - 1 ||
    date.getDate() !== Number(day)
  ) {
    throw new Error(`Enter a valid ${fieldLabel}.`);
  }
  return date;
}

function localDateValue(date: Date): string {
  const part = (value: number) => String(value).padStart(2, '0');
  return `${date.getFullYear()}-${part(date.getMonth() + 1)}-${part(date.getDate())}`;
}

export function buildRecordHistoryFilters(input: {
  recordType: WellnessRecordType | 'all';
  startDate: string;
  endDate: string;
}): WellnessRecordListFilters {
  const filters: WellnessRecordListFilters = {};
  if (input.recordType !== 'all') {
    filters.recordType = input.recordType;
  }

  const hasStart = input.startDate.trim().length > 0;
  const hasEnd = input.endDate.trim().length > 0;
  if (hasStart !== hasEnd) {
    throw new Error('Choose both a start date and an end date, or leave both blank.');
  }
  if (!hasStart || !hasEnd) {
    return filters;
  }

  const startDate = parsedLocalDate(input.startDate, 'start date');
  const endDate = parsedLocalDate(input.endDate, 'end date');
  if (endDate.getTime() < startDate.getTime()) {
    throw new Error('End date must be the same as or later than start date.');
  }

  const endExclusive = new Date(endDate);
  endExclusive.setDate(endExclusive.getDate() + 1);
  filters.start = localDateTimeToAwareIso(`${localDateValue(startDate)}T00:00`);
  filters.end = localDateTimeToAwareIso(`${localDateValue(endExclusive)}T00:00`);
  return filters;
}
