import type { DashboardRoutineEntry, DashboardSummary } from '../types';
import { formatPercent } from './format';

/**
 * Turns the role-scoped `/dashboard/summary` payload into the tiles the home
 * screen renders.
 *
 * Kept pure and separate from the screen so the role mapping — including the
 * rule that a `null` attendance percentage means "nothing recorded yet" rather
 * than 0% — is unit-testable without a renderer.
 */
export interface DashboardTile {
  key: string;
  label: string;
  value: string;
  hint?: string;
  /** Renders the tile with the warning accent (e.g. attendance below 75%). */
  warning?: boolean;
}

export interface DashboardView {
  role: DashboardSummary['role'];
  tiles: DashboardTile[];
  unreadNotifications: number;
  /** Today's classes, already scoped to the caller by the server. */
  todayClasses: DashboardRoutineEntry[];
}

const EMPTY: DashboardView = { role: 'student', tiles: [], unreadNotifications: 0, todayClasses: [] };

export function summarizeDashboard(summary: DashboardSummary | undefined): DashboardView {
  if (!summary) return EMPTY;

  switch (summary.role) {
    case 'student':
    case 'cr': {
      const s = summary.student;
      if (!s) return { ...EMPTY, role: summary.role };
      return {
        role: summary.role,
        unreadNotifications: s.unread_notifications,
        todayClasses: s.routine,
        tiles: [
          {
            key: 'attendance',
            label: 'Attendance',
            value: formatPercent(s.attendance_percentage),
            hint:
              s.attendance_percentage === null
                ? 'No classes recorded yet'
                : s.below_attendance_threshold
                  ? 'Below the 75% threshold'
                  : `${s.attended} of ${s.total_classes} classes attended`,
            warning: s.below_attendance_threshold === true,
          },
          {
            key: 'courses',
            label: 'Enrolled courses',
            value: String(s.enrolled_courses),
            hint: `${s.credit_hours} credit hours`,
          },
          {
            key: 'today',
            label: "Today's classes",
            value: String(s.today_classes),
            hint: s.today_classes === 0 ? 'Nothing scheduled' : 'Check the schedule tab',
          },
          {
            key: 'opportunities',
            label: 'Open opportunities',
            value: String(s.opportunities),
            hint: 'Career openings still accepting applications',
          },
        ],
      };
    }

    case 'teacher': {
      const t = summary.teacher;
      if (!t) return { ...EMPTY, role: summary.role };
      return {
        role: summary.role,
        unreadNotifications: t.unread_notifications,
        todayClasses: [],
        tiles: [
          { key: 'assigned', label: 'Assigned courses', value: String(t.assigned_courses) },
          { key: 'students', label: 'Students taught', value: String(t.students_taught) },
          { key: 'today', label: "Today's classes", value: String(t.today_classes) },
          {
            key: 'requests',
            label: 'Pending requests',
            value: String(t.pending_equipment_requests + t.pending_room_requests + t.pending_project_proposals),
            hint: `${t.pending_equipment_requests} equipment · ${t.pending_room_requests} room · ${t.pending_project_proposals} project`,
          },
        ],
      };
    }

    case 'lab_assistant': {
      const e = summary.er;
      if (!e) return { ...EMPTY, role: summary.role };
      return {
        role: summary.role,
        unreadNotifications: e.unread_notifications,
        todayClasses: [],
        tiles: [
          { key: 'equipment', label: 'Equipment', value: String(e.equipment_total) },
          {
            key: 'repair',
            label: 'Under repair',
            value: String(e.equipment_under_repair),
            warning: e.equipment_under_repair > 0,
          },
          { key: 'borrow', label: 'Borrow requests', value: String(e.pending_borrow_requests) },
          { key: 'rooms', label: 'Rooms', value: String(e.rooms_total), hint: `${e.pending_room_requests} pending` },
        ],
      };
    }

    case 'alumni': {
      const a = summary.alumni;
      if (!a) return { ...EMPTY, role: summary.role };
      return {
        role: summary.role,
        unreadNotifications: a.unread_notifications,
        todayClasses: [],
        tiles: [
          { key: 'visible', label: 'Alumni in directory', value: String(a.visible_alumni) },
          { key: 'active', label: 'Active alumni', value: String(a.active_alumni) },
          { key: 'mentorship', label: 'Mentorship pairs', value: String(a.mentorship_pairs) },
          { key: 'careers', label: 'Career openings', value: String(a.career_opportunities) },
        ],
      };
    }

    case 'super_admin': {
      const a = summary.admin;
      if (!a) return { ...EMPTY, role: summary.role };
      return {
        role: summary.role,
        unreadNotifications: a.unread_notifications,
        todayClasses: [],
        tiles: [
          {
            key: 'users',
            label: 'Users',
            value: String(a.users_total),
            hint: `${a.users_active} active`,
          },
          {
            key: 'approvals',
            label: 'Pending approvals',
            value: String(a.pending_approvals),
            warning: a.pending_approvals > 0,
          },
          { key: 'courses', label: 'Courses', value: String(a.courses) },
          { key: 'projects', label: 'Projects', value: String(a.projects) },
        ],
      };
    }

    default:
      return { ...EMPTY, role: summary.role };
  }
}
