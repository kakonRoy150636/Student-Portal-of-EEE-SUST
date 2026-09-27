import React from 'react';
import { Bell } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { Avatar } from '@/components/shared/Avatar';
import { ThemeSwitcher } from '@/components/shared/ThemeSwitcher';
import { ROLE_LABEL } from '@/layouts/nav';

interface DashboardHeroProps {
  consoleName?: string;
  roleName: string;
  /** Only rendered when a count is actually known. */
  unreadNotifications?: number;
  greetingHint?: string;
}

/**
 * Identity header for every role dashboard.
 *
 * Greeting and current context sit first. Theme and account facts stay
 * secondary so the first viewport is scan-friendly rather than decorative.
 */
export const DashboardHero = ({
  consoleName,
  roleName,
  unreadNotifications,
  greetingHint,
}: DashboardHeroProps) => {
  const { user } = useAuth();
  const name = user?.full_name || 'there';
  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';

  return (
    <section className="surface p-5 sm:p-6">
      <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-center">
        <div className="flex items-start gap-4">
          <Avatar
            avatarKey={user?.avatar_key}
            fullName={user?.full_name}
            className="h-14 w-14 text-lg"
            alt={`${name}'s profile photo`}
          />
          <div>
            <p className="kicker">{consoleName ?? ROLE_LABEL[roleName.toLowerCase()] ?? roleName}</p>
            <h1 className="mt-1 font-display text-xl font-bold tracking-tight text-[var(--text)] sm:text-[28px] sm:leading-[34px]">
              {greeting}, {name}
            </h1>
            <p className="mt-1 text-sm text-[var(--text-muted)]">
              {greetingHint ?? 'Department of Electrical and Electronic Engineering · SUST'}
            </p>
          </div>
        </div>

        <div className="grid w-full gap-3 sm:grid-cols-3 lg:w-auto lg:min-w-[22rem]">
          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] px-3 py-2.5">
            <p className="text-xs text-[var(--text-subtle)]">Student ID</p>
            <p className="mt-0.5 text-sm font-semibold text-[var(--text)]">{user?.identifier || '—'}</p>
          </div>
          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] px-3 py-2.5">
            <p className="flex items-center gap-1 text-xs text-[var(--text-subtle)]">
              <Bell className="h-3.5 w-3.5" /> Notices
            </p>
            <p className="mt-0.5 text-sm font-semibold text-[var(--text)]">
              {typeof unreadNotifications === 'number' ? `${unreadNotifications} unread` : '—'}
            </p>
          </div>
          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] px-3 py-2.5">
            <p className="text-xs text-[var(--text-subtle)]">Appearance</p>
            <div className="mt-1">
              <ThemeSwitcher />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
