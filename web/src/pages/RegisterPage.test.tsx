import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import { ApiError } from '../api/client';
import { AuthContext } from '../auth/authContext';
import { createAuthValue, currentUser } from '../test/authTestUtils';
import { LoginPage } from './LoginPage';
import { RegisterPage } from './RegisterPage';

function renderRegister(overrides = {}) {
  const value = createAuthValue(overrides);
  render(
    <AuthContext.Provider value={value}>
      <MemoryRouter initialEntries={['/register']}>
        <Routes>
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/login" element={<LoginPage />} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
  return value;
}

async function completeForm(
  password = 'long-enough-password',
  confirmation = password,
) {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText('Email address'), 'new@example.com');
  await user.type(screen.getByLabelText('Password', { exact: true }), password);
  await user.type(screen.getByLabelText('Confirm password'), confirmation);
  await user.click(screen.getByRole('button', { name: 'Create account' }));
}

describe('RegisterPage', () => {
  it('provides accessible controls and the backend password limits', () => {
    renderRegister();

    expect(
      screen.getByRole('heading', { name: 'Create your account' }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText('Password', { exact: true })).toHaveAttribute(
      'minlength',
      '12',
    );
    expect(screen.getByText('Use 12–256 characters.')).toBeInTheDocument();
    expect(screen.getByLabelText('Confirm password')).toHaveAttribute(
      'type',
      'password',
    );
  });

  it('prevents submission when password confirmation does not match', async () => {
    const register = vi.fn(async () => currentUser);
    renderRegister({ register });

    await completeForm('long-enough-password', 'different-password');

    expect(register).not.toHaveBeenCalled();
    expect(screen.getByText('Passwords must match.')).toBeInTheDocument();
    expect(screen.getByLabelText('Confirm password')).toHaveAttribute(
      'aria-invalid',
      'true',
    );
  });

  it('creates an account without auto-login and directs the user to sign in', async () => {
    const register = vi.fn(async () => currentUser);
    const login = vi.fn(async () => currentUser);
    renderRegister({ register, login });

    await completeForm();

    expect(register).toHaveBeenCalledWith({
      email: 'new@example.com',
      password: 'long-enough-password',
    });
    expect(login).not.toHaveBeenCalled();
    expect(
      await screen.findByText('Account created. Sign in to continue.'),
    ).toBeInTheDocument();
    expect(screen.getByLabelText('Email address')).toHaveValue(
      'new@example.com',
    );
  });

  it('renders the duplicate-account response safely', async () => {
    const register = vi.fn(async () => {
      throw new ApiError('An account with this email already exists.', {
        kind: 'api',
        status: 409,
        code: 'account_already_exists',
      });
    });
    renderRegister({ register });

    await completeForm();

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'An account with this email already exists.',
    );
  });
});
