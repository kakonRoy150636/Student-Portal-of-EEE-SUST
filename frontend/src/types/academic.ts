export interface Course {
  id: string;
  course_code: string;
  title: string;
  credit_hours: number;
  type: string;
}

/** Shape returned by GET /courses (the catalogue endpoint calls credits `credits`). */
export interface CourseCatalogueItem {
  id: string;
  course_code: string;
  title: string;
  credits: number;
  type: string;
  description: string | null;
}

export interface Semester {
  id: number;
  title: string;
  is_active: boolean;
  start_date: string;
  end_date: string;
  /** The term used to scope teacher-provided courses and student selection. */
  target_term?: string | null;
}

export type OfferingPublicationStatus = 'draft' | 'published';
export type TeacherAssignmentRequestStatus = 'pending' | 'approved' | 'rejected';
export type EnrollmentStatus = 'enrolled' | 'main' | 'improvement' | 'drop';
export type ActiveEnrollmentStatus = Exclude<EnrollmentStatus, 'drop'>;

export interface TeacherAssignmentRequest {
  id: string;
  course_offering_id: string;
  teacher_id: string;
  teacher_name: string;
  course_code: string;
  course_title: string;
  semester_id: number;
  semester_title: string;
  status: TeacherAssignmentRequestStatus;
  decided_by: string | null;
  decided_at: string | null;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface TeacherAssignmentRequestFilters {
  status?: TeacherAssignmentRequestStatus;
}

export interface CourseOfferingCreatePayload {
  course_id: string;
  semester_id: number;
}

export type CourseProvisionType = 'theory' | 'lab';

export interface CourseOfferingProvidePayload {
  course_code: string;
  title: string;
  credit_hours: number;
  course_type: CourseProvisionType;
  semester_id: number;
  description?: string;
}

export interface CourseOfferingUpdatePayload {
  course_id?: string;
  semester_id?: number;
}

export type AssignmentDecision = 'approve' | 'reject';

export interface AssignmentDecisionPayload {
  decision: AssignmentDecision;
  rejection_reason?: string | null;
}

export interface RosterEntry {
  student_id: string;
  identifier: string;
  full_name: string;
  email: string;
  status: ActiveEnrollmentStatus;
  credit_hours: number;
}

export interface AssignedCourseTeacher {
  teacher_id: string;
  teacher_name: string;
  role: string;
}

export interface CourseOffering {
  id: string;
  course_id: string;
  semester_id: number;
  semester_title: string;
  semester_is_active: boolean;
  course_code: string;
  course_title: string;
  course_type: string;
  credit_hours: number;
  publication_status: OfferingPublicationStatus;
  assigned_teachers: AssignedCourseTeacher[];
  created_by: string | null;
  published_by: string | null;
  published_at: string | null;
  request_status: TeacherAssignmentRequestStatus | null;
  /** Present when the offering is scoped to a matching student/teacher term. */
  target_term?: string | null;
}

export interface CourseEnrollment {
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

export interface EnrollmentSelection {
  enrollment_type: ActiveEnrollmentStatus;
}

export interface ActiveCreditTotal {
  active_credit_total: number;
}

export interface ClassSchedule {
  id: string;
  course_code: string;
  course_title: string;
  day_of_week: string;
  start_time: string;
  end_time: string;
  room_number: string;
  instructor_name: string;
  is_lab: boolean;
}

export interface AttendanceSummary {
  total_classes: number;
  attended: number;
  percentage: number;
  below_threshold: boolean;
  per_course: Record<string, { present: number; total: number }>;
}

export interface AcademicResource {
  id: string;
  title: string;
  description: string | null;
  category: string;
  course_id: string;
  uploader_id: string;
  file_key: string;
  file_name: string;
  file_size_bytes: number;
  mime_type: string;
  download_count: number;
  is_faculty_verified: boolean;
  created_at: string;
  updated_at: string;
}

export interface CareerOpportunity {
  title: string;
  organization: string;
  deadline: string;
}

export interface CapstoneProject {
  title: string;
  tier: string;
}
