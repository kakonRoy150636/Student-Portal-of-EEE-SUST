import React from 'react';
import type { AlumniEmployment } from '../api/alumniApi';

const formatDate = (value: string | null) => value ? new Date(`${value}T00:00:00`).toLocaleDateString('en-US', { month: 'short', year: 'numeric' }) : 'Unknown';

export function CareerTimeline({ employments }: { employments: AlumniEmployment[] }) {
  if (!employments.length) return <p className="text-sm text-[var(--text-muted)]">No career timeline has been published.</p>;
  return <ol className="relative space-y-6 border-l border-[var(--border)] pl-6">
    {employments.map((employment) => <li key={employment.id} className="relative">
      <span className="absolute -left-[1.65rem] top-1 h-3 w-3 rounded-full bg-[var(--accent-bright)] ring-4 ring-[var(--bg)]" />
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-semibold text-[var(--text)]">{employment.position}</p>
          <p className="text-sm text-[var(--text-muted)]">{employment.organization}</p>
        </div>
        {employment.is_current && <span className="rounded-full bg-[var(--success-soft)] px-2 py-1 text-xs font-semibold text-[var(--success)]">Current</span>}
      </div>
      <p className="mt-1 text-xs text-[var(--text-subtle)]">{formatDate(employment.start_date)} — {employment.is_current ? 'Present' : formatDate(employment.end_date)}</p>
      <p className="mt-1 text-xs capitalize text-[var(--text-muted)]">{employment.sector.replace('_', ' ')}{employment.city || employment.country ? ` · ${[employment.city, employment.country].filter(Boolean).join(', ')}` : ''}</p>
    </li>)}
  </ol>;
}
