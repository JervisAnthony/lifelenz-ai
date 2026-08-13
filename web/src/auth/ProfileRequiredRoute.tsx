import { Navigate, Outlet } from 'react-router-dom';

import { useAuth } from './authContext';

export function ProfileRequiredRoute() {
  const { user } = useAuth();
  if (!user?.profile_ids.length) {
    return <Navigate to="/app/profile" replace />;
  }
  return <Outlet />;
}
