import type { UserRole } from '../types';

const ROLE_LABELS: Record<UserRole, string> = {
  student: 'Student',
  cr: 'Class Representative',
  teacher: 'Teacher',
  lab_assistant: 'Lab Assistant (ER)',
  alumni: 'Alumni',
  super_admin: 'Administrator',
};

export function roleLabel(role: UserRole | undefined): string {
  if (!role) return 'Member';
  return ROLE_LABELS[role] ?? 'Member';
}

/** Up to two initials for the avatar placeholder. */
export function initials(fullName: string | undefined): string {
  if (!fullName) return '?';
  const parts = fullName.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

/** Roles that can hold course enrolments (`STUDENT_OR_CR` on the backend). */
export function hasEnrollments(role: UserRole | undefined): boolean {
  return role === 'student' || role === 'cr';
}

/** Percentages arrive as floats; show one decimal only when it adds information. */
export function formatPercent(value: number | null): string {
  if (value === null || Number.isNaN(value)) return '—';
  const rounded = Math.round(value * 10) / 10;
  return `${Number.isInteger(rounded) ? rounded : rounded.toFixed(1)}%`;
}

/** Short absolute timestamp for notification rows. */
export function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleString(undefined, {
    day: 'numeric',
    month: 'short',
    hour: 'numeric',
    minute: '2-digit',
  });
}
