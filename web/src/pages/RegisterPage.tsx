import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/authContext';
import { registrationErrorMessage } from '../auth/messages';
import { Alert } from '../components/Alert';
import { AuthLayout } from '../components/AuthLayout';
import { Button } from '../components/Button';
import { Field } from '../components/Field';

export function RegisterPage() {
  const navigate = useNavigate();
  const { register } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [confirmationError, setConfirmationError] = useState<string | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (password !== confirmation) {
      setConfirmationError('Passwords must match.');
      return;
    }
    setConfirmationError(null);
    setIsSubmitting(true);
    try {
      await register({ email, password });
      setPassword('');
      setConfirmation('');
      navigate('/login', {
        replace: true,
        state: { registrationComplete: true, email },
      });
    } catch (caughtError) {
      setError(registrationErrorMessage(caughtError));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AuthLayout
      title="Create your account"
      intro="Begin with an account. Your wellness profile remains a separate next step."
      alternateText="Already have an account?"
      alternateLink="/login"
      alternateLabel="Sign in"
    >
      {error ? <Alert>{error}</Alert> : null}
      <form className="auth-form" onSubmit={handleSubmit}>
        <Field
          id="register-email"
          name="email"
          label="Email address"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
          disabled={isSubmitting}
        />
        <Field
          id="register-password"
          name="password"
          label="Password"
          type="password"
          autoComplete="new-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          hint="Use 12–256 characters."
          required
          minLength={12}
          maxLength={256}
          disabled={isSubmitting}
        />
        <Field
          id="register-confirmation"
          name="password-confirmation"
          label="Confirm password"
          type="password"
          autoComplete="new-password"
          value={confirmation}
          onChange={(event) => setConfirmation(event.target.value)}
          error={confirmationError ?? undefined}
          required
          minLength={12}
          maxLength={256}
          disabled={isSubmitting}
        />
        <Button
          className="auth-form__submit"
          type="submit"
          disabled={isSubmitting}
        >
          {isSubmitting ? 'Creating account…' : 'Create account'}
        </Button>
      </form>
    </AuthLayout>
  );
}
