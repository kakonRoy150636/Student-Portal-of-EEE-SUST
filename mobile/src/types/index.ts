/**
 * Types mirroring the backend schemas the mobile client consumes.
 *
 * These are hand-written against `backend/app/schemas/*` rather than generated,
 * so a field rename on the server shows up here as a TypeScript error at the
 * call site instead of `undefined` on the screen.
 */

/** `backend/app/models/user.py::UserRole`. */
export type UserRole = 'super_admin' | 'teacher' | 'cr' | 'student' | 'lab_assistant' | 'alumni';

/** `AuthSessionResponse.user` — `backend/app/schemas/auth.py`. */
export interface User {
  id: string;
  identifier: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  avatar_key: string | null;
}

/**
 * Login takes an institutional identifier (student ID, `faculty-…`, or admin
 * handle), *not* an email address: `LoginRequest.identifier`.
 */
export interface LoginRequest {
  identifier: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

/** The refresh token is never in this body — it is an HttpOnly cookie. */
export interface AuthSessionResponse {
  user: User;
  tokens: TokenResponse;
}

export type EnrollmentStatus = 'enrolled' | 'main' | 'improvement' | 'drop';

/** `EnrollmentResponse` — `backend/app/schemas/academic.py`. */
export interface Enrollment {
  id: number;
  course_offering_id: string;
  student_id: string;
  status: EnrollmentStatus;
  course_code: string;
  course_title: string;
  semester_id: number;
  semester_title: string;
  credit_hours: number;
  enrolled_at: string;
  updated_at: string;
  dropped_at: string | null;
}

export interface ActiveCreditTotal {
  active_credit_total: number;
}

/** `GET /schedules/my-routine` — `ScheduleService.get_my_routine`. */
export interface RoutineEntry {
  id: string;
  course_code: string;
  course_title: string;
  day_of_week: string;
  start_time: string | null;
  end_time: string | null;
  room_number: string | null;
  instructor_name: string | null;
  is_lab: boolean;
}

/** `GET /dashboard/summary` — `backend/app/schemas/dashboard.py`. */
export interface DashboardRoutineEntry {
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
  /** `null` until at least one class has been recorded — not the same as 0%. */
  attendance_percentage: number | null;
  below_attendance_threshold: boolean | null;
  credit_hours: number;
  today_classes: number;
  routine: DashboardRoutineEntry[];
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

/** Only the section matching `role` is populated; the rest stay `null`. */
export interface DashboardSummary {
  role: UserRole;
  student: StudentSummary | null;
  teacher: TeacherSummary | null;
  er: ErSummary | null;
  alumni: AlumniSummary | null;
  admin: AdminSummary | null;
}

/** `NotificationResponse` — `backend/app/schemas/notification.py`. */
export interface PortalNotification {
  id: number;
  title: string;
  body: string;
  is_read: boolean;
  created_at: string;
  data_payload: Record<string, unknown>;
}

/** `GET /notifications/summary`. */
export interface NotificationSummary {
  items: PortalNotification[];
  unread_count: number;
}
