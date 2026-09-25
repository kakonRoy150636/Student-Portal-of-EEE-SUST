import React from 'react';
import { Cpu } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { Avatar } from '@/components/shared/Avatar';
import { ThemeSwitcher } from '@/components/shared/ThemeSwitcher';

interface DashboardHeroProps {
  consoleName: string;
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
      <div className="relative z-10 flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div className="space-y-2">
          <div className="flex items-center gap-3 font-mono text-xs">
            <span
              className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded border font-bold text-[10px] tracking-wider uppercase"
              style={{
                backgroundColor: 'var(--accent-soft)',
                borderColor: 'var(--accent-edge)',
                color: 'var(--accent-bright)',
              }}
            >
              <Cpu className="h-3 w-3" />
              {consoleName}
            </span>
            <span className="text-slate-400 text-[11px] uppercase">{roleName}</span>
          </div>
          <div className="flex items-center gap-4">
            <Avatar
              avatarKey={user?.avatar_key}
              fullName={user?.full_name}
              className="h-14 w-14 md:h-16 md:w-16 text-lg"
              alt={`${name}'s profile photo`}
            />
            <div>
              <h1 className="text-3xl md:text-4xl font-black tracking-tight text-white font-mono uppercase">{name}</h1>
              <p className="text-xs font-mono" style={{ color: 'var(--accent-bright)' }}>
                DEPARTMENT OF ELECTRICAL &amp; ELECTRONIC ENGINEERING // SUST
              </p>
            </div>
          </div>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-4 font-mono text-xs space-y-2 min-w-[16rem]">
          <div className="flex items-center justify-between gap-4">
            <span className="text-slate-400">ACCOUNT:</span>
            <span className="font-bold text-white">{user?.identifier || '—'}</span>
          </div>
          <div className="flex items-center justify-between gap-4 border-t border-slate-800/80 pt-2">
            <span className="text-slate-400">UNREAD ALERTS:</span>
            <span className="font-bold" style={{ color: 'var(--accent-bright)' }}>
              {typeof unreadNotifications === 'number' ? unreadNotifications : '—'}
            </span>
          </div>
          {/* Wraps so the three-mode switcher drops to its own line on narrow
              screens rather than pushing past the card edge. */}
          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-800/80 pt-2">
            <span className="text-slate-400">COLOR MODE:</span>
            <ThemeSwitcher />
          </div>
        </div>
      </div>
    </div>
  );
};
