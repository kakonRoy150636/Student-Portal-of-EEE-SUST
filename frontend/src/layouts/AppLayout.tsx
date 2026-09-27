import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { Breadcrumbs } from './components/Breadcrumbs';
import { MobileBottomNav, MobileDrawer } from './components/MobileNav';

export const AppLayout = () => {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="relative flex min-h-screen bg-[var(--bg)] text-[var(--text)]">
      <div className="dashboard-plate" aria-hidden="true" />

      <Sidebar />
      <MobileDrawer open={mobileOpen} onClose={() => setMobileOpen(false)} />

      <div className="relative z-10 flex min-w-0 flex-1 flex-col">
        <Header onOpenMobileNav={() => setMobileOpen(true)} />
        <main className="mx-auto w-full max-w-6xl flex-1 overflow-y-auto px-4 py-6 pb-24 sm:px-6 md:pb-8">
          <Breadcrumbs />
          <Outlet />
        </main>
      </div>
      <MobileBottomNav />
    </div>
  );
};
