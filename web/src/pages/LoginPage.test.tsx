import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import { ApiError } from '../api/client';
import { AuthContext } from '../auth/authContext';
import { createAuthValue, currentUser } from '../test/authTestUtils';
import { LoginPage } from './LoginPage';

function renderLogin(overrides = {}) {
  const value = createAuthValue(overrides);
  render(
    <AuthContext.Provider value={value}>
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/app" element={<h1>Authenticated home</h1>} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
  return value;
}

describe('LoginPage', () => {
  it('provides accessible email, password, and submit controls', () => {
    renderLogin();

    expect(
      screen.getByRole('heading', { name: 'Welcome back' }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText('Email address')).toHaveAttribute(
      'type',
      'email',
    );
    expect(screen.getByLabelText('Password')).toHaveAttribute(
      'type',
      'password',
    );
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeEnabled();
    expect(
      screen.getByRole('link', { name: 'Create an account' }),
    ).toHaveAttribute('href', '/register');
  });

  it('submits credentials and navigates after authoritative login succeeds', async () => {
    const login = vi.fn(async () => currentUser);
    renderLogin({ login });
    const user = userEvent.setup();

    await user.type(
      screen.getByLabelText('Email address'),
      'person@example.com',
    );
    await user.type(screen.getByLabelText('Password'), 'long-enough-password');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(login).toHaveBeenCalledWith({
      email: 'person@example.com',
      password: 'long-enough-password',
    });
    expect(
      await screen.findByRole('heading', { name: 'Authenticated home' }),
    ).toBeInTheDocument();
  });

  it('shows a generic invalid-credentials error and clears the password', async () => {
    const login = vi.fn(async () => {
      throw new ApiError('backend detail', {
        kind: 'api',
        status: 401,
        code: 'invalid_credentials',
      });
    });
    renderLogin({ login });
    const user = userEvent.setup();

    await user.type(
      screen.getByLabelText('Email address'),
      'person@example.com',
    );
    await user.type(screen.getByLabelText('Password'), 'long-enough-password');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Invalid email or password.',
    );
    expect(screen.getByLabelText('Password')).toHaveValue('');
  });
});
