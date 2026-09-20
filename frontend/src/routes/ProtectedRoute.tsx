import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { UserRole } from '@/types/auth';

export const ProtectedRoute = ({ children, roles }: { children: JSX.Element; roles?: UserRole[] }) => {
  const { isAuthenticated, role, loading } = useAuth();
  if (loading) return <div className="p-8 text-center text-xs text-slate-400">Authenticating...</div>;
  if (!isAuthenticated) return <Navigate to="/auth/login" replace />;
  if (roles && role && !roles.includes(role)) return <Navigate to="/dashboard" replace />;
  return children;
};
