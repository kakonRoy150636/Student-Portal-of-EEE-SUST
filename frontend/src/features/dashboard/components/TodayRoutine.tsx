import React from 'react';
import { Clock, MapPin, CalendarDays, ArrowUpRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { RoutineEntry } from '@/features/dashboard/types/dashboard';

interface TodayRoutineProps {
  routine?: RoutineEntry[] | null;
  loading?: boolean;
}

export const TodayRoutine = ({ routine, loading = false }: TodayRoutineProps) => {
  const classes = routine ?? [];

  return (
    <section className="surface flex flex-col p-5">
      <div className="flex items-center justify-between gap-3 border-b border-[var(--border)] pb-3">
        <h2 className="flex items-center gap-2 font-display text-base font-semibold text-[var(--text)]">
          <CalendarDays className="h-4 w-4 text-[var(--accent-bright)]" />
          Today&apos;s schedule
        </h2>
        <span className="text-xs font-semibold uppercase tracking-wide text-[var(--text-subtle)]">
          {loading ? 'Loading' : `${classes.length} class${classes.length === 1 ? '' : 'es'}`}
        </span>
      </div>

      {loading ? (
        <div className="mt-4 space-y-3" aria-hidden="true">
          {[0, 1].map((i) => (
            <div key={i} className="h-[88px] animate-pulse rounded-xl bg-[var(--surface-muted)]" />
          ))}
        </div>
      ) : classes.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 py-10 text-center">
          <CalendarDays className="h-7 w-7 text-[var(--text-subtle)]" />
          <p className="text-sm font-medium text-[var(--text)]">No classes scheduled today</p>
          <p className="text-sm text-[var(--text-muted)]">Nothing is published for your enrolled courses.</p>
          <Link
            to="/schedule"
            className="mt-1 inline-flex items-center gap-1 text-sm font-semibold text-[var(--accent-bright)] hover:underline"
          >
            Open full schedule <ArrowUpRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      ) : (
        <ul className="mt-4 space-y-3">
          {classes.map((lec, index) => (
            <li
              key={`${lec.course_code}-${lec.start_time}-${index}`}
              className="rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <span className="text-xs font-bold uppercase tracking-wide text-[var(--accent-bright)]">
                    {lec.course_code}
                  </span>
                  <h3 className="mt-1 truncate text-sm font-semibold text-[var(--text)]">{lec.course_title}</h3>
                </div>
                {lec.start_time && (
                  <div className="flex shrink-0 items-center gap-1 text-xs text-[var(--text-muted)]">
                    <Clock className="h-3.5 w-3.5" />
                    <span>
                      {lec.start_time}
                      {lec.end_time ? ` – ${lec.end_time}` : ''}
                    </span>
                  </div>
                )}
              </div>
              {lec.room_number && (
                <div className="mt-3 flex items-center gap-1.5 border-t border-[var(--border)] pt-2.5 text-xs text-[var(--text-muted)]">
                  <MapPin className="h-3.5 w-3.5 shrink-0" />
                  <span className="truncate">
                    {lec.room_number}
                    {lec.building ? `, ${lec.building}` : ''}
                  </span>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
};
