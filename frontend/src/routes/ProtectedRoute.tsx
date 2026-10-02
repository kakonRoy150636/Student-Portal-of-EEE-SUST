import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { UserRole } from '@/types/auth';

const SECURITY_PATH = '/account/security';

export const ProtectedRoute = ({ children, roles }: { children: JSX.Element; roles?: UserRole[] }) => {
  const { isAuthenticated, role, user, loading } = useAuth();
  const location = useLocation();
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--bg)] px-6">
        <p className="text-sm text-[var(--text-muted)]">Checking your session…</p>
      </div>
    );
  }
  if (!isAuthenticated) return <Navigate to="/auth/login" replace />;

  // Unfinished security chores take precedence over wherever the user was
  // heading. The API enforces the same rule, so this is a courtesy redirect,
  // not the control itself.
  const mustFinishSecurity =
    (user?.must_change_password ||
      (role === UserRole.SUPER_ADMIN && user?.mfa_enabled === false)) &&
    location.pathname !== SECURITY_PATH;
  if (mustFinishSecurity) return <Navigate to={SECURITY_PATH} replace />;

  if (roles && role && !roles.includes(role)) return <Navigate to="/dashboard" replace />;
  return children;
};
