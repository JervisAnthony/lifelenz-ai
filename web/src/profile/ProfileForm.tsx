import { useState, type FormEvent } from 'react';

import type {
  TrackedWellnessDomain,
  WellnessProfileRequest,
} from '../api/types';
import { Alert } from '../components/Alert';
import { Button } from '../components/Button';
import { Field } from '../components/Field';
import {
  measurementSystemOptions,
  trackedDomainOptions,
  weekStartOptions,
} from './profileOptions';

interface ProfileFormProps {
  initialValue: WellnessProfileRequest;
  mode: 'create' | 'edit';
  isSubmitting: boolean;
  error: string | null;
  success: string | null;
  onSubmit(value: WellnessProfileRequest): Promise<void>;
}

export function ProfileForm({
  initialValue,
  mode,
  isSubmitting,
  error,
  success,
  onSubmit,
}: ProfileFormProps) {
  const [value, setValue] = useState(initialValue);

  function toggleDomain(domain: TrackedWellnessDomain) {
    setValue((current) => ({
      ...current,
      tracked_domains: current.tracked_domains.includes(domain)
        ? current.tracked_domains.filter((item) => item !== domain)
        : [...current.tracked_domains, domain],
    }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSubmit({
      ...value,
      display_name: value.display_name?.trim() || null,
      time_zone: value.time_zone.trim(),
    });
  }

  return (
    <form
      className="profile-form"
      onSubmit={(event) => void handleSubmit(event)}
    >
      {error ? <Alert>{error}</Alert> : null}
      {success ? <Alert tone="success">{success}</Alert> : null}

      <section
        className="profile-form__section"
        aria-labelledby="profile-basics-heading"
      >
        <div className="profile-form__section-heading">
          <span>01</span>
          <div>
            <h2 id="profile-basics-heading">Your preferences</h2>
            <p>
              Set a friendly name and the time zone used for future local-date
              views.
            </p>
          </div>
        </div>
        <div className="profile-form__fields">
          <Field
            id="display-name"
            name="display-name"
            label="Display name (optional)"
            type="text"
            autoComplete="nickname"
            value={value.display_name ?? ''}
            onChange={(event) =>
              setValue({ ...value, display_name: event.target.value })
            }
            hint="Used only to make your LifeLenz space feel familiar."
            disabled={isSubmitting}
          />
          <Field
            id="time-zone"
            name="time-zone"
            label="Time zone"
            type="text"
            value={value.time_zone}
            onChange={(event) =>
              setValue({ ...value, time_zone: event.target.value })
            }
            hint="Use UTC or an IANA identifier such as Asia/Kolkata."
            required
            disabled={isSubmitting}
          />
        </div>
      </section>

      <fieldset className="profile-form__section">
        <legend className="profile-form__section-heading">
          <span>02</span>
          <span>
            <strong>Measurement preference</strong>
            <small>
              Stored for future presentation. Summary values remain in canonical
              units.
            </small>
          </span>
        </legend>
        <div className="choice-grid choice-grid--two">
          {measurementSystemOptions.map((option) => (
            <label className="choice-card" key={option.value}>
              <input
                type="radio"
                name="measurement-system"
                value={option.value}
                checked={value.measurement_system === option.value}
                onChange={() =>
                  setValue({ ...value, measurement_system: option.value })
                }
                disabled={isSubmitting}
              />
              <span>
                <strong>{option.label}</strong>
                <small>{option.description}</small>
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset className="profile-form__section">
        <legend className="profile-form__section-heading">
          <span>03</span>
          <span>
            <strong>Week starts on</strong>
            <small>This preference will shape future calendar groupings.</small>
          </span>
        </legend>
        <div className="choice-grid choice-grid--two">
          {weekStartOptions.map((option) => (
            <label
              className="choice-card choice-card--compact"
              key={option.value}
            >
              <input
                type="radio"
                name="week-start"
                value={option.value}
                checked={value.week_start === option.value}
                onChange={() =>
                  setValue({ ...value, week_start: option.value })
                }
                disabled={isSubmitting}
              />
              <strong>{option.label}</strong>
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset className="profile-form__section">
        <legend className="profile-form__section-heading">
          <span>04</span>
          <span>
            <strong>Areas you want to track</strong>
            <small>
              Choose any that feel useful. You can change these preferences
              later.
            </small>
          </span>
        </legend>
        <div className="domain-grid">
          {trackedDomainOptions.map((option) => (
            <label className="domain-option" key={option.value}>
              <input
                type="checkbox"
                checked={value.tracked_domains.includes(option.value)}
                onChange={() => toggleDomain(option.value)}
                disabled={isSubmitting}
              />
              <span>
                <strong>{option.label}</strong>
                <small>{option.description}</small>
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      <div className="profile-form__actions">
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting
            ? 'Saving…'
            : mode === 'create'
              ? 'Complete setup'
              : 'Save preferences'}
        </Button>
        <p>Your profile stores preferences, not medical history.</p>
      </div>
    </form>
  );
}
