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
