import React from 'react';
import { Clock, MapPin, CalendarDays, ArrowUpRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { RoutineEntry } from '@/features/dashboard/types/dashboard';

interface TodayRoutineProps {
  routine?: RoutineEntry[] | null;
  loading?: boolean;
}

/**
 * Today's timetable, resolved from class_schedules.
 *
 * The previous version rendered two hardcoded lectures ("EEE 311 Electrical
 * Machines II, 09:00-10:30, Dr. M. Rahman") for every signed-in user and
 * reported "LAST_PING: 0.14ms" and "CR_BROADCAST: ACTIVE" that measured
 * nothing. An empty timetable now says so, and links to the full schedule.
 */
export const TodayRoutine = ({ routine, loading = false }: TodayRoutineProps) => {
  const classes = routine ?? [];

  return (
    <div className="hud-box corner-brackets rounded-xl p-5 flex flex-col">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 font-mono text-xs">
        <h2 className="text-slate-300 flex items-center gap-1.5 font-bold uppercase tracking-wider">
          <CalendarDays className="h-4 w-4" style={{ color: 'var(--accent-bright)' }} />
          Today&apos;s Timetable
        </h2>
        <span
          className="text-[10px] tracking-wider uppercase font-semibold"
          style={{ color: 'var(--accent-bright)' }}
        >
          {loading ? 'Loading' : `${classes.length} class${classes.length === 1 ? '' : 'es'}`}
        </span>
      </div>

      {loading ? (
        <div className="mt-4 space-y-3" aria-hidden="true">
          {[0, 1].map((i) => (
            <div key={i} className="h-[92px] animate-pulse rounded-lg border border-slate-800/80 bg-slate-900/40" />
          ))}
        </div>
      ) : classes.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 py-10 text-center">
          <CalendarDays className="h-8 w-8 text-slate-600" />
          <div>
            <p className="text-sm font-medium text-slate-300">No classes scheduled today</p>
            <p className="mt-1 text-xs font-mono text-slate-500">
              Nothing is published in the timetable for your enrolments.
            </p>
          </div>
          <Link
            to="/schedule"
            className="inline-flex items-center gap-1 text-xs font-mono font-bold hover:underline"
            style={{ color: 'var(--accent-bright)' }}
          >
            Open full schedule <ArrowUpRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      ) : (
        <ul className="mt-4 space-y-3">
          {classes.map((lec, index) => (
            <li
              key={`${lec.course_code}-${lec.start_time}-${index}`}
              className="rounded-lg border p-4 transition-all border-slate-800/80 bg-slate-900/40 hover:border-[var(--accent-edge)]"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <span className="font-mono text-xs font-black" style={{ color: 'var(--accent-bright)' }}>
                    {lec.course_code}
                  </span>
                  <h4 className="mt-1 font-bold text-sm text-slate-100 truncate">{lec.course_title}</h4>
                </div>
                {lec.start_time && (
                  <div className="flex items-center gap-1 text-xs font-mono text-slate-400 shrink-0">
                    <Clock className="h-3.5 w-3.5" style={{ color: 'var(--accent-bright)' }} />
                    <span>
                      {lec.start_time}
                      {lec.end_time ? ` – ${lec.end_time}` : ''}
                    </span>
                  </div>
                )}
              </div>

              {lec.room_number && (
                <div className="mt-3 flex items-center gap-1.5 text-xs font-mono text-slate-400 border-t border-slate-800/60 pt-2.5">
                  <MapPin className="h-3.5 w-3.5 text-slate-500 shrink-0" />
                  <span className="text-slate-300 truncate">
                    {lec.room_number}
                    {lec.building ? `, ${lec.building}` : ''}
                  </span>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};
