import { useState, type FormEvent } from 'react';

import type {
  GoalDirection,
  GoalStatus,
  MetricIdentifier,
  WellnessGoalRequest,
} from '../api/types';
import { Alert } from '../components/Alert';
import { Button } from '../components/Button';
import { Field } from '../components/Field';
import {
  directionOptions,
  metricDefinition,
  metricOptions,
  statusOptions,
  unitLabels,
} from './goalPresentation';
import { buildGoalRequest, type GoalFormValue } from './goalRequests';

const emptyGoal: GoalFormValue = {
  metric: 'sleep_duration',
  targetValue: '',
  direction: 'at_least',
  status: 'draft',
  startDate: '',
  targetDate: '',
  title: '',
  description: '',
};

function formValue(initialValue?: WellnessGoalRequest): GoalFormValue {
  if (!initialValue) {
    return emptyGoal;
  }
  return {
    metric: initialValue.target.metric,
    targetValue: String(initialValue.target.value),
    direction: initialValue.direction,
    status: initialValue.status,
    startDate: initialValue.start_date ?? '',
    targetDate: initialValue.target_date ?? '',
    title: initialValue.title ?? '',
    description: initialValue.description ?? '',
  };
}

export function GoalForm({
  initialValue,
  mode,
  isSaving,
  error,
  onSubmit,
  onCancel,
}: {
  initialValue?: WellnessGoalRequest;
  mode: 'create' | 'edit';
  isSaving: boolean;
  error?: string | null;
  onSubmit(request: WellnessGoalRequest): Promise<void>;
  onCancel?: () => void;
}) {
  const [value, setValue] = useState(() => formValue(initialValue));
  const [validationError, setValidationError] = useState<string | null>(null);
  const unit = metricDefinition(value.metric).unit;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setValidationError(null);
    let request: WellnessGoalRequest;
    try {
      request = buildGoalRequest(value);
    } catch (caughtError) {
      if (caughtError instanceof Error) {
        setValidationError(caughtError.message);
      }
      return;
    }
    await onSubmit(request).catch(() => undefined);
  }

  return (
    <form className="goal-form" onSubmit={(event) => void handleSubmit(event)}>
      {validationError ? <Alert>{validationError}</Alert> : null}
      {error ? <Alert>{error}</Alert> : null}
      <div className="goal-form__grid">
        <div className="field">
          <label htmlFor={`${mode}-goal-metric`}>Metric</label>
          <select
            id={`${mode}-goal-metric`}
            value={value.metric}
            onChange={(event) =>
              setValue({
                ...value,
                metric: event.target.value as MetricIdentifier,
              })
            }
            disabled={isSaving}
          >
            {metricOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        <Field
          id={`${mode}-goal-target`}
          label="Target value"
          type="number"
          min="0"
          step="any"
          value={value.targetValue}
          onChange={(event) =>
            setValue({ ...value, targetValue: event.target.value })
          }
          required
          disabled={isSaving}
        />
        <div className="field">
          <span id={`${mode}-goal-unit-label`}>Canonical unit</span>
          <output
            className="goal-form__unit"
            aria-labelledby={`${mode}-goal-unit-label`}
          >
            {unitLabels[unit]}
          </output>
        </div>
        <div className="field">
          <label htmlFor={`${mode}-goal-direction`}>Direction</label>
          <select
            id={`${mode}-goal-direction`}
            value={value.direction}
            onChange={(event) =>
              setValue({
                ...value,
                direction: event.target.value as GoalDirection,
              })
            }
            disabled={isSaving}
          >
            {directionOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor={`${mode}-goal-status`}>Status</label>
          <select
            id={`${mode}-goal-status`}
            value={value.status}
            onChange={(event) =>
              setValue({
                ...value,
                status: event.target.value as GoalStatus,
              })
            }
            disabled={isSaving}
          >
            {statusOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        <Field
          id={`${mode}-goal-start-date`}
          label="Start date (optional)"
          type="date"
          value={value.startDate}
          onChange={(event) =>
            setValue({ ...value, startDate: event.target.value })
          }
          disabled={isSaving}
        />
        <Field
          id={`${mode}-goal-target-date`}
          label="Target date (optional)"
          type="date"
          min={value.startDate || undefined}
          value={value.targetDate}
          onChange={(event) =>
            setValue({ ...value, targetDate: event.target.value })
          }
          disabled={isSaving}
        />
        <Field
          id={`${mode}-goal-title`}
          label="Title (optional)"
          type="text"
          value={value.title}
          onChange={(event) =>
            setValue({ ...value, title: event.target.value })
          }
          disabled={isSaving}
        />
      </div>
      <div className="field">
        <label htmlFor={`${mode}-goal-description`}>
          Description (optional)
        </label>
        <textarea
          id={`${mode}-goal-description`}
          rows={3}
          value={value.description}
          onChange={(event) =>
            setValue({ ...value, description: event.target.value })
          }
          disabled={isSaving}
        />
      </div>
      <div className="goal-form__actions">
        <Button type="submit" disabled={isSaving}>
          {isSaving
            ? 'Saving…'
            : mode === 'create'
              ? 'Create goal'
              : 'Save goal changes'}
        </Button>
        {onCancel ? (
          <Button
            variant="quiet"
            type="button"
            onClick={onCancel}
            disabled={isSaving}
          >
            Cancel edit
          </Button>
        ) : null}
        <p>Values use the backend's canonical unit and are not evaluated.</p>
      </div>
    </form>
  );
}
