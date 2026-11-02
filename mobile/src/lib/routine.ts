import type { RoutineEntry } from '../types';

/**
 * The academic week in Bangladesh runs Sunday → Thursday, so sorting by
 * `new Date(day).getDay()` or by English alphabetical order would both put
 * the week in the wrong order for students.
 */
export const WEEK_ORDER = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'] as const;

export type WeekDay = (typeof WEEK_ORDER)[number];

export function dayIndex(day: string): number {
  const index = WEEK_ORDER.findIndex((entry) => entry.toLowerCase() === day.trim().toLowerCase());
  // Unknown values sort last instead of silently landing at the top.
  return index === -1 ? WEEK_ORDER.length : index;
}

/** Full day name for a date, matching the `day_of_week` values the API stores. */
export function dayName(date: Date = new Date()): WeekDay {
  return WEEK_ORDER[date.getDay()];
}

/** Parses the API's "10:00 AM" / "14:05" strings into minutes since midnight. */
export function timeToMinutes(time: string | null): number {
  if (!time) return Number.MAX_SAFE_INTEGER;
  const match = /^(\d{1,2}):(\d{2})\s*(AM|PM)?$/i.exec(time.trim());
  if (!match) return Number.MAX_SAFE_INTEGER;

  let hours = Number(match[1]);
  const minutes = Number(match[2]);
  const meridiem = match[3]?.toUpperCase();
  if (meridiem === 'PM' && hours < 12) hours += 12;
  if (meridiem === 'AM' && hours === 12) hours = 0;
  return hours * 60 + minutes;
}

/** Sorts a routine into week order, then by start time within each day. */
export function sortRoutine(entries: RoutineEntry[]): RoutineEntry[] {
  return [...entries].sort((a, b) => {
    const byDay = dayIndex(a.day_of_week) - dayIndex(b.day_of_week);
    if (byDay !== 0) return byDay;
    return timeToMinutes(a.start_time) - timeToMinutes(b.start_time);
  });
}

export interface RoutineDay {
  day: string;
  entries: RoutineEntry[];
}

/** Groups a routine into consecutive day sections, in week order. */
export function groupRoutineByDay(entries: RoutineEntry[]): RoutineDay[] {
  const groups = new Map<string, RoutineEntry[]>();
  for (const entry of sortRoutine(entries)) {
    const key = entry.day_of_week.trim();
    const bucket = groups.get(key);
    if (bucket) bucket.push(entry);
    else groups.set(key, [entry]);
  }
  return [...groups.entries()].map(([day, dayEntries]) => ({ day, entries: dayEntries }));
}

/** Entries scheduled for `today`, already in start-time order. */
export function todayRoutine(entries: RoutineEntry[], today: Date = new Date()): RoutineEntry[] {
  const name = dayName(today).toLowerCase();
  return sortRoutine(entries.filter((entry) => entry.day_of_week.trim().toLowerCase() === name));
}

/** "10:00 AM – 11:30 AM", or a single time when the end is missing. */
export function formatTimeRange(start: string | null, end: string | null): string {
  if (!start && !end) return 'Time not set';
  if (start && end) return `${start} – ${end}`;
  return start ?? end ?? 'Time not set';
}
