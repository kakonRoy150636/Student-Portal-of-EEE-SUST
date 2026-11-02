export type Role = 'student' | 'teacher' | 'admin' | 'alumni';

export interface User {
  id: string;
  email: string;
  fullName: string;
  role: Role;
  department?: string;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
}

export interface Course {
  id: string;
  code: string;
  title: string;
  credits: number;
  teacher?: string;
  enrolled?: boolean;
}
