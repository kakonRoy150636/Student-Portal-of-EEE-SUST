import React from 'react';
import type { AttendanceSummary } from '@/types/academic';

export const RollCallGrid = ({ summary }: { summary: AttendanceSummary }) => {
  const courses = Object.entries(summary.per_course ?? {});

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div className="surface p-4">
          <p className="text-xs uppercase tracking-wide text-[var(--text-subtle)]">Recorded</p>
          <p className="mt-1 font-display text-xl font-bold">{summary.percentage}%</p>
        </div>
        <div className="surface p-4">
          <p className="text-xs uppercase tracking-wide text-[var(--text-subtle)]">Present</p>
          <p className="mt-1 font-display text-xl font-bold">{summary.attended} / {summary.total_classes}</p>
        </div>
        <div className="surface p-4">
          <p className="text-xs uppercase tracking-wide text-[var(--text-subtle)]">Standing</p>
          <p className="mt-1 font-display text-xl font-bold" style={{ color: summary.below_threshold ? 'var(--danger)' : 'var(--success)' }}>
            {summary.below_threshold ? 'Below 75%' : 'On track'}
          </p>
        </div>
      </div>

      <div className="hidden overflow-hidden rounded-card border border-[var(--border)] bg-[var(--surface)] md:block">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide text-[var(--text-subtle)]">
              <th className="px-4 py-3">Course offering</th>
              <th className="px-4 py-3">Present</th>
              <th className="px-4 py-3">Sessions</th>
            </tr>
          </thead>
          <tbody>
            {courses.map(([offering, row]) => (
              <tr key={offering} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-3 font-medium">{offering}</td>
                <td className="px-4 py-3">{row.present}</td>
                <td className="px-4 py-3">{row.total}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="space-y-3 md:hidden">
        {courses.map(([offering, row]) => (
          <article key={offering} className="surface p-4 text-sm">
            <p className="font-semibold">{offering}</p>
            <p className="mt-1 text-[var(--text-muted)]">{row.present} present of {row.total} sessions</p>
          </article>
        ))}
      </div>
    </div>
  );
};
