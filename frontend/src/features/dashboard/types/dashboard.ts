/**
 * Shapes returned by GET /dashboard/summary.
 *
 * Only the section matching the caller's role is populated; the rest stay
 * null, which is how the server enforces that a student cannot read
 * department-wide totals by calling the endpoint directly.
 */

export interface RoutineEntry {
  course_code: string;
  course_title: string;
  day_of_week: string;
  start_time: string | null;
  end_time: string | null;
  room_number: string | null;
  building: string | null;
}

export interface StudentSummary {
  enrolled_courses: number;
  total_classes: number;
  attended: number;
  /** null when no class has been recorded yet -- not the same as 0%. */
  attendance_percentage: number | null;
  below_attendance_threshold: boolean | null;
  credit_hours: number;
  today_classes: number;
  routine: RoutineEntry[];
  unread_notifications: number;
  opportunities: number;
}

export interface TeacherSummary {
  assigned_courses: number;
  students_taught: number;
  today_classes: number;
  pending_equipment_requests: number;
  pending_room_requests: number;
  pending_project_proposals: number;
  unread_notifications: number;
}

export interface ErSummary {
  equipment_total: number;
  equipment_under_repair: number;
  pending_borrow_requests: number;
  rooms_total: number;
  pending_room_requests: number;
  unread_notifications: number;
}

export interface AlumniSummary {
  visible_alumni: number;
  active_alumni: number;
  mentorship_pairs: number;
  career_opportunities: number;
  unread_notifications: number;
}

export interface AdminSummary {
  users_total: number;
  users_active: number;
  pending_approvals: number;
  users_by_role: Record<string, number>;
  pending_alumni_claims: number;
  active_alumni: number;
  pending_room_requests: number;
  rooms_total: number;
  equipment_total: number;
  pending_equipment_requests: number;
  courses: number;
  projects: number;
  unread_notifications: number;
}

export type UserRoleKey =
  | 'super_admin' | 'teacher' | 'cr' | 'student' | 'lab_assistant' | 'alumni';

export interface DashboardSummary {
  role: UserRoleKey;
  student: StudentSummary | null;
  teacher: TeacherSummary | null;
  er: ErSummary | null;
  alumni: AlumniSummary | null;
  admin: AdminSummary | null;
}
