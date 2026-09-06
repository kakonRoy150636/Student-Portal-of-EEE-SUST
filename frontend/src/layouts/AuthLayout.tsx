import React from 'react';
import { Outlet } from 'react-router-dom';

export const AuthLayout = () => (
  <div className="min-h-screen flex items-center justify-center bg-slate-100 dark:bg-slate-950 p-4">
    <div className="w-full max-w-md bg-white dark:bg-slate-900 rounded-xl shadow-md p-6 border border-slate-200 dark:border-slate-800">
      <Outlet />
    </div>
  </div>
);
