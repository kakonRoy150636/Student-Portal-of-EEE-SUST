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
  /** True for a bootstrapped admin or after a reset: only security routes work. */
  must_change_password?: boolean;
  mfa_enabled?: boolean;
}

export interface LoginCredentials {
  identifier: string;
  password: string;
}

export interface MfaSetup {
  secret: string;
  otpauth_uri: string;
}

export interface SessionSummary {
  family_id: string;
  created_at?: string | null;
  last_used_at?: string | null;
  ip_address?: string | null;
  user_agent?: string | null;
  is_current: boolean;
  is_active: boolean;
}
