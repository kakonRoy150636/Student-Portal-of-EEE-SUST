export enum UserRole {
  SUPER_ADMIN = "super_admin",
  TEACHER = "teacher",
  CR = "cr",
  STUDENT = "student",
  LAB_ASSISTANT = "lab_assistant",
  /** Mirrors backend/app/models/user.py::UserRole.ALUMNI, which already existed. */
  ALUMNI = "alumni"
}

export interface User {
  id: string;
  identifier: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  /** Storage key of the uploaded avatar, e.g. "avatars/<uuid>.jpg". */
  avatar_key?: string | null;
}

export interface LoginCredentials {
  identifier: string;
  password: string;
}
