import React from 'react';
import { ArrowUpRight, BookOpen, CalendarDays, FolderKanban, MessageSquare } from 'lucide-react';
import { Link } from 'react-router-dom';
import campusImage from '@/assets/images/login-hero.jpg';
import { QuickStats } from '../../components/QuickStats';
import { TodayRoutine } from '../../components/TodayRoutine';
import { AttendanceGauge } from '../../components/AttendanceGauge';
import { useDashboardSummary } from '../../hooks/useDashboardSummary';

export const StudentDashboardPage = () => {
  const { data, isLoading, isError } = useDashboardSummary();
  const s = data?.student;

  return (
    <div className="student-editorial-page relative z-10 space-y-8">
      <section className="editorial-hero" aria-labelledby="student-home-heading">
        <img src={campusImage} alt="SUST campus building" className="editorial-hero-image" />
        <div className="editorial-hero-wash" />
        <div className="editorial-hero-topline">
          <span>SUST / EEE</span>
          <span>STUDENT PORTAL</span>
        </div>
        <div className="editorial-hero-copy">
          <p className="editorial-kicker">Your academic day, in view</p>
          <h1 id="student-home-heading">Learn with<br />purpose.</h1>
          <p className="editorial-hero-description">
            One place for your classes, attendance, resources, and the next step in your engineering journey.
          </p>
        </div>
        <div className="editorial-hero-meta">
          <span>DEPARTMENT OF EEE</span>
          <span>SYLHET, BANGLADESH</span>
        </div>
      </section>

      <section className="editorial-snapshot" aria-labelledby="snapshot-heading">
        <div className="editorial-snapshot-heading">
          <div>
            <p className="editorial-kicker">Live from your account</p>
            <h2 id="snapshot-heading">Academic snapshot</h2>
          </div>
          <div className="editorial-snapshot-note">
            <span className="editorial-status-dot" />
            <span>{s?.unread_notifications ?? 0} unread notification{s?.unread_notifications === 1 ? '' : 's'}</span>
          </div>
        </div>
        <QuickStats data={s} loading={isLoading} />
      </section>

      {isError && (
        <div
          className="rounded-xl border p-4 text-sm"
          style={{ borderColor: 'rgba(251,113,133,0.4)', backgroundColor: 'rgba(251,113,133,0.08)', color: '#FB7185' }}
          role="alert"
        >
          Live counters are unavailable right now. The API did not return the
          dashboard summary, so no figures are shown rather than showing stale ones.
        </div>
      )}
      <section aria-labelledby="quick-actions-heading">
        <div className="mb-3 flex items-end justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: 'var(--accent-bright)' }}>
              Start here
            </p>
            <h2 id="quick-actions-heading" className="mt-1 text-xl font-bold text-white">Quick actions</h2>
          </div>
          <p className="hidden text-sm text-slate-400 sm:block">Common tools for your study day</p>
        </div>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[
            { label: 'View schedule', detail: 'Check today and upcoming classes', href: '/schedule', icon: CalendarDays },
            { label: 'Review attendance', detail: 'See your class records', href: '/attendance', icon: BookOpen },
            { label: 'Open resources', detail: 'Find notes and course files', href: '/resources', icon: FolderKanban },
            { label: 'Ask the AI assistant', detail: 'Get help with academic topics', href: '/ai', icon: MessageSquare },
          ].map(({ label, detail, href, icon: Icon }) => (
            <Link
              key={href}
              to={href}
              className="group rounded-xl border border-slate-800/80 bg-slate-950/55 p-4 transition-colors hover:border-[var(--accent-edge)] hover:bg-slate-900/75"
            >
              <Icon className="h-5 w-5" style={{ color: 'var(--accent-bright)' }} />
              <div className="mt-4 flex items-start justify-between gap-2">
                <div>
                  <h3 className="text-sm font-semibold text-slate-100">{label}</h3>
                  <p className="mt-1 text-xs leading-5 text-slate-400">{detail}</p>
                </div>
                <ArrowUpRight className="h-4 w-4 shrink-0 text-slate-500 transition-colors group-hover:text-[var(--accent-bright)]" />
              </div>
            </Link>
          ))}
        </div>
      </section>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <TodayRoutine routine={s?.routine} loading={isLoading} />
        <AttendanceGauge data={s} loading={isLoading} />
      </div>
    </div>
  );
};
