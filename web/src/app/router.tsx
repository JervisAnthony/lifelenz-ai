import { createBrowserRouter } from 'react-router-dom';

import { ProtectedRoute, PublicOnlyRoute } from '../auth/ProtectedRoute';
import { AppShell } from '../components/AppShell';
import { DashboardPage } from '../pages/DashboardPage';
import { LandingPage } from '../pages/LandingPage';
import { LoginPage } from '../pages/LoginPage';
import { NotFoundPage } from '../pages/NotFoundPage';
import { RegisterPage } from '../pages/RegisterPage';

export const appRoutes = [
  {
    path: '/',
    element: <LandingPage />,
  },
  {
    element: <PublicOnlyRoute />,
    children: [
      { path: '/login', element: <LoginPage /> },
      { path: '/register', element: <RegisterPage /> },
    ],
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        path: '/app',
        element: <AppShell />,
        children: [{ index: true, element: <DashboardPage /> }],
      },
    ],
  },
  {
    path: '*',
    element: <NotFoundPage />,
  },
];

export function createAppRouter() {
  return createBrowserRouter(appRoutes);
}
