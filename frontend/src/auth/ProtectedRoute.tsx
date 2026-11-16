import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from './AuthContext';

export const SessionLoading: React.FC = () => (
  <div className="session-loading" role="status">
    <span className="session-spinner" aria-hidden="true" />
    <span>Checking your session…</span>
  </div>
);

export const ProtectedRoute: React.FC = () => {
  const { status } = useAuth();
  const location = useLocation();

  if (status === 'loading') {
    return <SessionLoading />;
  }

  if (status === 'anonymous') {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: location.pathname }}
      />
    );
  }

  return <Outlet />;
};

export const GuestRoute: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const { status } = useAuth();

  if (status === 'loading') {
    return <SessionLoading />;
  }

  if (status === 'authenticated') {
    return <Navigate to="/account" replace />;
  }

  return <>{children}</>;
};
