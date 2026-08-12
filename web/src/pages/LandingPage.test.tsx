import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import { LandingPage } from './LandingPage';

describe('LandingPage', () => {
  it('offers discoverable login and registration actions without medical claims', () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>,
    );

    expect(
      screen.getByRole('heading', {
        name: 'Notice the patterns that make your days feel different.',
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('navigation', { name: 'Account navigation' }),
    ).toBeInTheDocument();
    expect(
      screen.getAllByRole('link', {
        name: /create account|start your private space/i,
      }),
    ).toHaveLength(2);
    expect(
      screen.getByText(/does not provide medical advice/i),
    ).toBeInTheDocument();
  });
});
