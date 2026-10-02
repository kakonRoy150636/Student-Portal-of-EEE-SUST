export interface Course {
  id: string;
  course_code: string;
  title: string;
  credit_hours: number;
  type: string;
}

export interface Semester {
  id: number;
  title: string;
  is_active: boolean;
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
  /** Null for a department-wide resource. */
  course_code: string | null;
  file_name: string;
  file_size_bytes: number;
  mime_type: string;
  download_count: number;
  is_faculty_verified: boolean;
  uploader_name?: string | null;
  created_at: string;
}

export interface CareerOpportunity {
  id: string;
  title: string;
  organization_name: string;
  type: string;
  location: string | null;
  application_deadline: string;
  application_target: string;
  description: string;
  tags: string[];
}

export interface CapstoneProject {
  id: string;
  title: string;
  abstract: string;
  tier: string;
  supervisor_name: string | null;
  github_repo_url: string | null;
  member_count: number;
}
