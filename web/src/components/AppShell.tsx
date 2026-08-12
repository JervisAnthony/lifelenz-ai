import { NavLink, Outlet, useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/authContext';
import { Brand } from './Brand';
import { Button } from './Button';

export function AppShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate('/login', { replace: true });
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Brand to="/app" />
        <nav aria-label="Application navigation">
          <NavLink to="/app" end>
            <span aria-hidden="true">⌂</span>
            Home
          </NavLink>
        </nav>
        <p className="sidebar__note">
          A clearer view of your everyday patterns.
        </p>
      </aside>
      <div className="app-shell__body">
        <header className="app-header">
          <div className="app-header__mobile-brand">
            <Brand to="/app" />
          </div>
          <div className="account-control">
            <span className="account-control__email">{user?.email}</span>
            <Button variant="quiet" type="button" onClick={handleLogout}>
              Sign out
            </Button>
          </div>
        </header>
        <main className="app-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
