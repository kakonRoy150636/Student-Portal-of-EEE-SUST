import React from 'react';
import { ArrowUpRight, BookOpen, CalendarDays, FolderKanban, MessageSquare } from 'lucide-react';
import { Link } from 'react-router-dom';
import { QuickStats } from '../../components/QuickStats';
import { TodayRoutine } from '../../components/TodayRoutine';
import { AttendanceGauge } from '../../components/AttendanceGauge';
import { DashboardHero } from './DashboardHero';
import { useDashboardSummary } from '../../hooks/useDashboardSummary';

export const StudentDashboardPage = () => {
  const { data, isLoading, isError } = useDashboardSummary();
  const s = data?.student;

  return (
    <div className="space-y-6">
      <DashboardHero
        roleName="STUDENT"
        unreadNotifications={s?.unread_notifications}
        greetingHint="Current semester snapshot for your enrolled courses."
      />

      {isError && (
        <div
          className="rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] p-4 text-sm text-[var(--danger)]"
          role="alert"
        >
          Live counters are unavailable right now. No figures are shown rather than showing stale ones.
        </div>
      )}

      <QuickStats data={s} loading={isLoading} />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <TodayRoutine routine={s?.routine} loading={isLoading} />
        <AttendanceGauge data={s} loading={isLoading} />
      </div>

      <section aria-labelledby="pending-heading" className="surface p-5">
        <div className="mb-3 flex items-end justify-between gap-3">
          <div>
            <p className="kicker">Pending actions</p>
            <h2 id="pending-heading" className="mt-1 font-display text-lg font-semibold">
              Start here
            </h2>
          </div>
          <p className="hidden text-sm text-[var(--text-muted)] sm:block">
            {s?.unread_notifications ?? 0} unread notice{(s?.unread_notifications ?? 0) === 1 ? '' : 's'}
          </p>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {[
            { label: 'View schedule', detail: 'Today and upcoming classes', href: '/schedule', icon: CalendarDays },
            { label: 'Review attendance', detail: 'See your class records', href: '/attendance', icon: BookOpen },
            { label: 'Open resources', detail: 'Find notes and course files', href: '/resources', icon: FolderKanban },
            { label: 'Ask the assistant', detail: 'Help with academic topics', href: '/ai', icon: MessageSquare },
          ].map(({ label, detail, href, icon: Icon }) => (
            <Link
              key={href}
              to={href}
              className="group rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-4 transition-colors hover:border-[var(--accent-edge)]"
            >
              <Icon className="h-5 w-5 text-[var(--accent-bright)]" />
              <div className="mt-3 flex items-start justify-between gap-2">
                <div>
                  <h3 className="text-sm font-semibold text-[var(--text)]">{label}</h3>
                  <p className="mt-1 text-xs leading-5 text-[var(--text-muted)]">{detail}</p>
                </div>
                <ArrowUpRight className="h-4 w-4 shrink-0 text-[var(--text-subtle)] group-hover:text-[var(--accent-bright)]" />
              </div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
};
