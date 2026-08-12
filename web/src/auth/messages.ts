import { ApiError } from '../api/client';

export function loginErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (
      error.code === 'invalid_credentials' ||
      error.code === 'inactive_account'
    ) {
      return 'Invalid email or password.';
    }
    if (error.kind === 'network') {
      return "We couldn't reach LifeLenz. Please try again.";
    }
  }
  return 'We could not sign you in. Please try again.';
}

export function registrationErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === 'account_already_exists') {
      return 'An account with this email already exists.';
    }
    if (error.kind === 'network') {
      return "We couldn't reach LifeLenz. Please try again.";
    }
    if (error.status === 422) {
      return 'Please check your email and password, then try again.';
    }
  }
  return 'We could not create your account. Please try again.';
}
