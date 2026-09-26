import React from 'react';
import { ShieldCheck, Crosshair } from 'lucide-react';
import type { StudentSummary } from '@/features/dashboard/types/dashboard';

interface AttendanceGaugeProps {
  data?: StudentSummary | null;
  loading?: boolean;
}

const THRESHOLD = 75;

/**
 * Attendance ring drawn from the real aggregate.
 *
 * The old version hardcoded `percentage = 88.5` and asserted "VERIFIED VIA
 * EEE RFID ROLL-CALL SYSTEM" for a portal that has no RFID hardware. Both the
 * number and that claim are gone: the arc is the same query the Attendance
 * page shows, and the footer states where the figure comes from.
 */
export const AttendanceGauge = ({ data, loading = false }: AttendanceGaugeProps) => {
  const hasData = (data?.total_classes ?? 0) > 0;
  const percentage = hasData ? (data?.attendance_percentage ?? 0) : 0;
  const radius = 56;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;
  const below = data?.below_attendance_threshold === true;

  return (
    <div className="hud-box corner-brackets rounded-xl p-5 flex flex-col">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 font-mono text-xs">
        <span className="text-slate-300 flex items-center gap-1.5 font-bold uppercase tracking-wider">
          <Crosshair className="h-4 w-4" style={{ color: 'var(--accent-bright)' }} />
          Attendance overview
        </span>
        {!loading && hasData && (
          <span
            className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded border"
            style={{
              borderColor: below ? 'rgba(251,113,133,0.4)' : 'var(--accent-edge)',
              backgroundColor: below ? 'rgba(251,113,133,0.1)' : 'var(--accent-soft)',
              color: below ? '#FB7185' : 'var(--accent-bright)',
            }}
          >
            <ShieldCheck className="h-3 w-3" />
            {below ? 'Below 75%' : 'On track'}
          </span>
        )}
      </div>

      <div className="flex flex-col sm:flex-row items-center justify-center gap-6 py-4">
        <div className="relative flex items-center justify-center">
          <svg className="h-36 w-36 -rotate-90 transform" aria-hidden="true">
            <circle cx="72" cy="72" r={radius} className="stroke-slate-800" strokeWidth="8" fill="transparent" />
            {hasData && (
              <circle
                cx="72"
                cy="72"
                r={radius}
                stroke={below ? '#FB7185' : 'var(--accent-bright)'}
                className="transition-all duration-1000 ease-out"
                strokeWidth="8"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                fill="transparent"
              />
            )}
          </svg>
          <div className="absolute flex flex-col items-center font-mono">
            {loading ? (
              <div className="h-7 w-16 animate-pulse rounded bg-slate-800/80" aria-hidden="true" />
            ) : hasData ? (
              <>
                <span className="text-2xl font-black text-white tabular-nums">{percentage}%</span>
                <span className="text-[9px] uppercase tracking-widest text-slate-400">RECORDED</span>
              </>
            ) : (
              <>
                <span className="text-2xl font-black text-slate-500">—</span>
                <span className="text-[9px] uppercase tracking-widest text-slate-500">NO DATA</span>
              </>
            )}
          </div>
        </div>

        <div className="flex-1 space-y-2.5 font-mono text-xs w-full">
          <div className="flex justify-between rounded bg-slate-900/80 border border-slate-800 p-2">
            <span className="text-slate-400">Minimum target</span>
            <span className="font-bold text-slate-200">{THRESHOLD}%</span>
          </div>
          <div className="flex justify-between rounded bg-slate-900/80 border border-slate-800 p-2">
            <span className="text-slate-400">Classes recorded</span>
            <span className="font-bold text-slate-200">{data?.total_classes ?? 0}</span>
          </div>
          <div className="flex justify-between rounded bg-slate-900/80 border border-slate-800 p-2">
            <span className="text-slate-400">Current standing</span>
            <span className="font-bold" style={{ color: below ? '#FB7185' : 'var(--accent-bright)' }}>
              {hasData ? (below ? 'Needs attention' : 'On track') : 'Not available'}
            </span>
          </div>
        </div>
      </div>

      <div className="pt-3 border-t border-slate-800/80 text-[10px] font-mono text-slate-500">
        {hasData
          ? `${data?.attended} present of ${data?.total_classes} recorded attendance classes`
          : 'No attendance sessions have been recorded for your enrolled courses yet'}
      </div>
    </div>
  );
};
