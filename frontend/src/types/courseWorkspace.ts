export type AnnouncementType =
  | 'general'
  | 'class_update'
  | 'class_cancelled'
  | 'exam'
  | 'assignment'
  | 'urgent'
  | 'resource'
  | 'administrative';

export type AnnouncementStatus = 'draft' | 'scheduled' | 'published' | 'archived';

export type AnnouncementAudience = 'enrolled_students' | 'cr_only' | 'teachers_only';
export type CourseEventType = 'class' | 'quiz' | 'midterm' | 'final' | 'viva' | 'assignment_deadline' | 'lab_exam' | 'presentation' | 'holiday' | 'other';
export type CourseQuestionStatus = 'open' | 'answered' | 'resolved' | 'closed';
export type CourseQuestionVisibility = 'course' | 'private';

export interface AnnouncementPermissions {
  can_manage: boolean;
  can_publish: boolean;
  can_edit: boolean;
  can_archive: boolean;
  can_pin: boolean;
}

export interface CourseAnnouncement extends AnnouncementPermissions {
  id: string;
  offering_id: string;
  author_id: string;
  author_name: string;
  title: string;
  body: string;
  announcement_type: AnnouncementType;
  status: AnnouncementStatus;
  audience: AnnouncementAudience;
  is_pinned: boolean;
  publish_at: string | null;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
  is_read: boolean;
}

export interface CourseAnnouncementFeed {
  items: CourseAnnouncement[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface CourseWorkspaceCourse {
  id: string;
  course_code: string;
  title: string;
  credit_hours: number;
  type: string;
  description: string | null;
}

export interface CourseWorkspaceSemester {
  id: number;
  title: string;
  target_term: string | null;
  is_active: boolean;
  start_date: string;
  end_date: string;
}

export interface CourseWorkspaceTeacher {
  teacher_id: string;
  teacher_name: string;
  role: string;
}

export interface CourseWorkspaceSchedule {
  id: string;
  day_of_week: string;
  start_time: string;
  end_time: string;
  room_number: string | null;
  instructor_name: string | null;
  is_lab: boolean | null;
}

export interface CourseWorkspaceResource {
  id: string;
  title: string;
  description: string | null;
  category: string;
  course_id: string;
  file_name: string;
  file_size_bytes: number;
  mime_type: string;
  download_count: number;
  is_faculty_verified: boolean;
  created_at: string;
  is_published: boolean;
  archived_at: string | null;
  can_manage: boolean;
}

export interface CourseEvent {
  id: string;
  offering_id: string;
  author_id: string;
  author_name: string;
  title: string;
  description: string | null;
  event_type: CourseEventType;
  starts_at: string;
  ends_at: string | null;
  location: string | null;
  reminder_minutes: number | null;
  is_published: boolean;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
  can_manage: boolean;
}

export interface CourseQuestion {
  id: string;
  offering_id: string;
  student_id: string;
  student_name: string;
  title: string;
  body: string;
  status: CourseQuestionStatus;
  visibility: CourseQuestionVisibility;
  answer_body: string | null;
  answered_by: string | null;
  answered_at: string | null;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
  can_manage: boolean;
  can_answer: boolean;
  can_edit: boolean;
}

export interface CourseWorkspace extends AnnouncementPermissions {
  offering_id: string;
  offering_status: 'draft' | 'published';
  course: CourseWorkspaceCourse;
  semester: CourseWorkspaceSemester;
  authorized_teachers: CourseWorkspaceTeacher[];
  active_enrollment_count: number;
  unread_announcement_count: number;
  recent_activity: CourseAnnouncement[];
  upcoming_schedules: CourseWorkspaceSchedule[];
  resources: CourseWorkspaceResource[];
  events: CourseEvent[];
  questions: CourseQuestion[];
  permissions: AnnouncementPermissions;
  links: Record<string, string>;
}

export interface CourseAnnouncementCreatePayload {
  title: string;
  body: string;
  announcement_type: AnnouncementType;
  status: 'draft' | 'scheduled' | 'published';
  audience: AnnouncementAudience;
  publish_at?: string | null;
}

export interface CourseAnnouncementUpdatePayload {
  title?: string;
  body?: string;
  announcement_type?: AnnouncementType;
  status?: 'draft' | 'scheduled' | 'published';
  audience?: AnnouncementAudience;
  publish_at?: string | null;
}

export interface CourseAnnouncementFeedParams {
  limit: number;
  offset: number;
  search?: string;
  status?: AnnouncementStatus;
  announcement_type?: AnnouncementType;
}

export interface CourseEventPayload {
  title: string;
  description?: string | null;
  event_type: CourseEventType;
  starts_at: string;
  ends_at?: string | null;
  location?: string | null;
  reminder_minutes?: number | null;
  is_published?: boolean;
}

export interface CourseQuestionCreatePayload {
  title: string;
  body: string;
  visibility: CourseQuestionVisibility;
}

export interface CourseQuestionAnswerPayload {
  answer_body: string;
  status: 'answered' | 'resolved' | 'closed';
}

export interface CourseResourceUpdatePayload {
  is_published?: boolean;
  archived?: boolean;
}

export interface CourseAnnouncementReadResponse {
  announcement_id: string;
  read_at: string;
  is_read: true;
}

export interface ResourceDownloadResponse {
  download_url: string;
  expires_in: number;
  file_name: string;
}
