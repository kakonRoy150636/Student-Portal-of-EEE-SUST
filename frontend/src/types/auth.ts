export enum UserRole {
  SUPER_ADMIN = "super_admin",
  TEACHER = "teacher",
  CR = "cr",
  STUDENT = "student",
  LAB_ASSISTANT = "lab_assistant"
}

export interface User {
  id: string;
  identifier: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
}

export interface LoginCredentials {
  identifier: string;
  password: string;
}

export interface CourseSelection {
  course_offering_id: string;
  enrollment_type: 'main' | 'drop' | 'improvement';
}

export interface TeacherRegisterRequest {
  full_name: string;
  email: string;
  password: string;
  avatar_key?: string;
}

export interface StudentRegisterRequest {
  full_name: string;
  identifier: string;
  email: string;
  password: string;
  role: 'student' | 'cr';
  session_year: string;
  current_term: string;
  avatar_key?: string;
  course_selections: CourseSelection[];
}

export interface RegisterResponse {
  message: string;
  requires_approval: boolean;
}
