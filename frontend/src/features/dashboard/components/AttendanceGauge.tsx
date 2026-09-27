import React from 'react';
import { ShieldCheck } from 'lucide-react';
import type { StudentSummary } from '@/features/dashboard/types/dashboard';

interface AttendanceGaugeProps {
  data?: StudentSummary | null;
  loading?: boolean;
}

const THRESHOLD = 75;

export const AttendanceGauge = ({ data, loading = false }: AttendanceGaugeProps) => {
  const hasData = (data?.total_classes ?? 0) > 0;
  const percentage = hasData ? (data?.attendance_percentage ?? 0) : 0;
  const radius = 56;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;
  const below = data?.below_attendance_threshold === true;

  return (
    <section className="surface flex flex-col p-5">
      <div className="flex items-center justify-between gap-3 border-b border-[var(--border)] pb-3">
        <h2 className="font-display text-base font-semibold text-[var(--text)]">Attendance summary</h2>
        {!loading && hasData && (
          <span
            className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold"
            style={{
              backgroundColor: below ? 'var(--danger-soft)' : 'var(--success-soft)',
              color: below ? 'var(--danger)' : 'var(--success)',
            }}
          >
            <ShieldCheck className="h-3 w-3" />
            {below ? 'Below 75%' : 'On track'}
          </span>
        )}
      </div>

      <div className="flex flex-col items-center justify-center gap-6 py-4 sm:flex-row">
        <div className="relative flex items-center justify-center">
          <svg className="h-36 w-36 -rotate-90 transform" aria-hidden="true">
            <circle cx="72" cy="72" r={radius} stroke="var(--border)" strokeWidth="8" fill="transparent" />
            {hasData && (
              <circle
                cx="72"
                cy="72"
                r={radius}
                stroke={below ? 'var(--danger)' : 'var(--accent)'}
                strokeWidth="8"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                fill="transparent"
              />
            )}
          </svg>
          <div className="absolute flex flex-col items-center">
            {loading ? (
              <div className="h-7 w-16 animate-pulse rounded bg-[var(--surface-muted)]" aria-hidden="true" />
            ) : hasData ? (
              <>
                <span className="font-display text-xl font-bold tabular-nums text-[var(--text)]">{percentage}%</span>
                <span className="text-xs uppercase tracking-wide text-[var(--text-subtle)]">Recorded</span>
              </>
            ) : (
              <>
                <span className="font-display text-xl font-bold text-[var(--text-subtle)]">—</span>
                <span className="text-xs uppercase tracking-wide text-[var(--text-subtle)]">No data</span>
              </>
            )}
          </div>
        </div>

        <div className="w-full flex-1 space-y-2 text-sm">
          <div className="flex justify-between rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] px-3 py-2">
            <span className="text-[var(--text-muted)]">Minimum target</span>
            <span className="font-semibold text-[var(--text)]">{THRESHOLD}%</span>
          </div>
          <div className="flex justify-between rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] px-3 py-2">
            <span className="text-[var(--text-muted)]">Classes recorded</span>
            <span className="font-semibold text-[var(--text)]">{data?.total_classes ?? 0}</span>
          </div>
          <div className="flex justify-between rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] px-3 py-2">
            <span className="text-[var(--text-muted)]">Current standing</span>
            <span className="font-semibold" style={{ color: below ? 'var(--danger)' : 'var(--accent-bright)' }}>
              {hasData ? (below ? 'Needs attention' : 'On track') : 'Not available'}
            </span>
          </div>
        </div>
      </div>

      <p className="border-t border-[var(--border)] pt-3 text-xs text-[var(--text-muted)]">
        {hasData
          ? `${data?.attended} present of ${data?.total_classes} recorded attendance classes`
          : 'No attendance sessions have been recorded for your enrolled courses yet'}
      </p>
    </section>
  );
};
