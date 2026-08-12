import { Navigate, Outlet, useLocation } from 'react-router-dom';

import { LoadingScreen } from '../components/LoadingScreen';
import { useAuth } from './authContext';

export function ProtectedRoute() {
  const { status } = useAuth();
  const location = useLocation();

  if (status === 'loading') {
    return <LoadingScreen label="Restoring your session" />;
  }
  if (status === 'unauthenticated') {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}

export function PublicOnlyRoute() {
  const { status } = useAuth();
  if (status === 'loading') {
    return <LoadingScreen label="Restoring your session" />;
  }
  if (status === 'authenticated') {
    return <Navigate to="/app" replace />;
  }
  return <Outlet />;
}
