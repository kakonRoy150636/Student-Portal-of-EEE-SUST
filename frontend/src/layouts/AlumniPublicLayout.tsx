import React from 'react';
import { Link, Outlet } from 'react-router-dom';
import { DeptCrest } from '@/components/shared/DeptCrest';

export const AlumniPublicLayout = () => (
  <div className="min-h-screen bg-[var(--bg)] text-[var(--text)]">
    <header className="border-b border-[var(--border)] bg-[var(--bg-elevated)]/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link to="/alumni-association" className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-[var(--accent-edge)] bg-[var(--accent-soft)]">
            <DeptCrest className="h-7 w-7 opacity-95" variant="mono" />
          </div>
          <div>
            <p className="font-display text-sm font-bold tracking-tight">SUST EEE Alumni</p>
            <p className="text-xs text-[var(--text-muted)]">Association portal</p>
          </div>
        </Link>
        <nav className="flex items-center gap-2 text-sm">
          <Link to="/auth/login" className="rounded-lg px-3 py-2 text-[var(--text-muted)] hover:text-[var(--text)]">
            Sign in
          </Link>
          <Link
            to="/auth/register?role=alumni"
            className="rounded-lg bg-[var(--primary)] px-3 py-2 font-semibold text-[var(--primary-fg)]"
          >
            Join as alumni
          </Link>
        </nav>
      </div>
    </header>
    <main>
      <Outlet />
    </main>
    <footer className="border-t border-[var(--border)] py-8 text-center text-xs text-[var(--text-muted)]">
      Department of Electrical &amp; Electronic Engineering, SUST
    </footer>
  </div>
);
