import type { WellnessRecord } from '../api/types';
import { recordTypeLabels } from './recordTypes';

const dateTimeFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'medium',
  timeStyle: 'short',
});

function formatDateTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? 'Recorded time unavailable'
    : dateTimeFormatter.format(date);
}

function beverageLabel(value: string): string {
  return value
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

export function presentRecord(record: WellnessRecord): {
  label: string;
  timestamp: string;
  summary: string;
} {
  const timestamp = formatDateTime(record.metadata.recorded_at);
  switch (record.record_type) {
    case 'sleep':
      return {
        label: recordTypeLabels.sleep,
        timestamp,
        summary: `${formatDateTime(record.data.period.start)} – ${formatDateTime(record.data.period.end)}`,
      };
    case 'hydration':
      return {
        label: recordTypeLabels.hydration,
        timestamp,
        summary: `${record.data.volume_milliliters.toLocaleString()} mL · ${beverageLabel(record.data.beverage_type)}`,
      };
    case 'subjective_check_in':
      return {
        label: recordTypeLabels.subjective_check_in,
        timestamp,
        summary: 'Private self-reported scores recorded',
      };
    default:
      return {
        label: recordTypeLabels[record.record_type],
        timestamp,
        summary: `Recorded ${timestamp}`,
      };
  }
}
