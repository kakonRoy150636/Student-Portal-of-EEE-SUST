import React from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { Breadcrumbs } from './components/Breadcrumbs';

export const AppLayout = () => (
  <div className="flex min-h-screen bg-slate-50 dark:bg-slate-950">
    <Sidebar />
    <div className="flex-1 flex flex-col">
      <Header />
      <main className="p-8 flex-1 overflow-y-auto max-w-7xl mx-auto w-full">
        <Breadcrumbs />
        <Outlet />
      </main>
    </div>
  </div>
);
