import { useState, type FormEvent } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/authContext';
import { loginErrorMessage } from '../auth/messages';
import { Alert } from '../components/Alert';
import { AuthLayout } from '../components/AuthLayout';
import { Button } from '../components/Button';
import { Field } from '../components/Field';

interface LoginLocationState {
  registrationComplete?: boolean;
  email?: string;
}

function readLoginState(value: unknown): LoginLocationState {
  if (typeof value !== 'object' || value === null) {
    return {};
  }
  const candidate = value as Record<string, unknown>;
  return {
    registrationComplete: candidate.registrationComplete === true,
    email: typeof candidate.email === 'string' ? candidate.email : undefined,
  };
}

export function LoginPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { login, notice, clearNotice } = useAuth();
  const locationState = readLoginState(location.state);
  const [email, setEmail] = useState(locationState.email ?? '');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    clearNotice();
    setIsSubmitting(true);
    try {
      await login({ email, password });
      setPassword('');
      navigate('/app', { replace: true });
    } catch (caughtError) {
      setPassword('');
      setError(loginErrorMessage(caughtError));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AuthLayout
      title="Welcome back"
      intro="Sign in to return to your personal wellness space."
      alternateText="New to LifeLenz?"
      alternateLink="/register"
      alternateLabel="Create an account"
    >
      {locationState.registrationComplete ? (
        <Alert tone="success">Account created. Sign in to continue.</Alert>
      ) : null}
      {notice ? <Alert tone="info">{notice}</Alert> : null}
      {error ? <Alert>{error}</Alert> : null}
      <form className="auth-form" onSubmit={handleSubmit}>
        <Field
          id="login-email"
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
          id="login-password"
          name="password"
          label="Password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
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
          {isSubmitting ? 'Signing in…' : 'Sign in'}
        </Button>
      </form>
    </AuthLayout>
  );
}
