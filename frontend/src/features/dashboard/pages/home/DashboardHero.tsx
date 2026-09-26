import React from 'react';
import { Bell, CalendarDays } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { Avatar } from '@/components/shared/Avatar';
import { ThemeSwitcher } from '@/components/shared/ThemeSwitcher';

interface DashboardHeroProps {
  consoleName?: string;
  roleName: string;
  /** Only rendered when a count is actually known. */
  unreadNotifications?: number;
}

/**
 * Identity header for every role dashboard.
 *
 * The previous version printed "SYSTEM STATUS: OPTIMAL" as a fixed string --
 * a claim about system health that nothing measured, and one a reviewer can
 * disprove just by asking what it monitors. The account and theme controls
 * that actually do something are kept; the fabricated telemetry is not.
 */
export const DashboardHero = ({ consoleName, roleName, unreadNotifications }: DashboardHeroProps) => {
  const { user } = useAuth();
  const name = user?.full_name || 'USER';

  return (
    <div className="hud-box corner-brackets rounded-2xl p-6 relative overflow-hidden">
      <div
        className="absolute top-0 right-0 w-96 h-full pointer-events-none"
        style={{
          background:
            'linear-gradient(to left, var(--accent-soft), color-mix(in srgb, var(--accent) 8%, transparent), transparent)',
        }}
      />
      <div className="relative z-10 flex flex-col justify-between gap-6 md:flex-row md:items-center">
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: 'var(--accent-bright)' }}>
            {consoleName ?? roleName}
          </p>
          <div className="flex items-center gap-4">
            <Avatar
              avatarKey={user?.avatar_key}
              fullName={user?.full_name}
              className="h-14 w-14 md:h-16 md:w-16 text-lg"
              alt={`${name}'s profile photo`}
            />
            <div>
              <h1 className="text-3xl md:text-4xl font-black tracking-tight text-white">Welcome back, {name}</h1>
              <p className="mt-1 text-sm text-slate-400">
                Department of Electrical and Electronic Engineering · SUST
              </p>
            </div>
          </div>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-4 text-xs space-y-2 min-w-[16rem]">
          <div className="flex items-center justify-between gap-4">
            <span className="text-slate-400">Student ID</span>
            <span className="font-semibold text-white">{user?.identifier || '—'}</span>
          </div>
          <div className="flex items-center justify-between gap-4 border-t border-slate-800/80 pt-2">
            <span className="flex items-center gap-2 text-slate-400"><Bell className="h-3.5 w-3.5" /> Notifications</span>
            <span className="font-semibold" style={{ color: 'var(--accent-bright)' }}>
              {typeof unreadNotifications === 'number' ? `${unreadNotifications} unread` : '—'}
            </span>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-800/80 pt-2">
            <span className="flex items-center gap-2 text-slate-400"><CalendarDays className="h-3.5 w-3.5" /> Role</span>
            <span className="font-semibold uppercase" style={{ color: 'var(--accent-bright)' }}>{roleName}</span>
          </div>
          <div className="flex items-center justify-between gap-2 border-t border-slate-800/80 pt-2">
            <span className="text-slate-400">Theme</span>
            <ThemeSwitcher />
          </div>
        </div>
      </div>
    </div>
  );
};
