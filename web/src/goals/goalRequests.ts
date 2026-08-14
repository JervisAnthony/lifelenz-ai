import type {
  GoalDirection,
  GoalStatus,
  MetricIdentifier,
  WellnessGoalRequest,
} from '../api/types';
import { metricDefinition } from './goalPresentation';

export interface GoalFormValue {
  metric: MetricIdentifier;
  targetValue: string;
  direction: GoalDirection;
  status: GoalStatus;
  startDate: string;
  targetDate: string;
  title: string;
  description: string;
}

function validDate(value: string, label: string): string {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    throw new Error(`Enter a complete ${label.toLowerCase()}.`);
  }
  const parsed = new Date(`${value}T00:00:00Z`);
  if (
    Number.isNaN(parsed.getTime()) ||
    parsed.toISOString().slice(0, 10) !== value
  ) {
    throw new Error(`Enter a valid ${label.toLowerCase()}.`);
  }
  return value;
}

export function buildGoalRequest(value: GoalFormValue): WellnessGoalRequest {
  const targetValue = Number(value.targetValue);
  if (
    value.targetValue === '' ||
    !Number.isFinite(targetValue) ||
    targetValue < 0
  ) {
    throw new Error('Target value must be a finite number of zero or more.');
  }
  const startDate = value.startDate
    ? validDate(value.startDate, 'start date')
    : null;
  const targetDate = value.targetDate
    ? validDate(value.targetDate, 'target date')
    : null;
  if (startDate !== null && targetDate !== null && targetDate < startDate) {
    throw new Error('Target date cannot be before the start date.');
  }
  return {
    target: {
      metric: value.metric,
      value: targetValue,
      unit: metricDefinition(value.metric).unit,
    },
    direction: value.direction,
    status: value.status,
    start_date: startDate,
    target_date: targetDate,
    title: value.title.trim() || null,
    description: value.description.trim() || null,
  };
}
