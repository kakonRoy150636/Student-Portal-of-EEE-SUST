import React from 'react';
import { useAuth } from '@/contexts/AuthContext';

export const Header = () => {
  const { user, logout } = useAuth();
  return (
    <header className="h-16 border-b bg-white dark:bg-slate-900 px-8 flex items-center justify-between">
      <div className="text-sm font-semibold text-slate-500">Department of Electrical & Electronic Engineering</div>
      <div className="flex items-center gap-4">
        <span className="text-xs font-bold">{user?.full_name}</span>
        <button onClick={logout} className="text-xs text-rose-500 hover:underline">Sign Out</button>
      </div>
    </header>
  );
};
