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
