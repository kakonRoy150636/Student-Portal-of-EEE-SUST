import { api } from '@/lib/axios';
import { LoginCredentials } from '@/types/auth';
import { RegisterResponse, StudentRegisterRequest, TeacherRegisterRequest } from '@/types/auth';

export const authApi = {
  login: (creds: LoginCredentials) => api.post('/auth/login', creds),
  logout: () => api.post('/auth/logout'),
  me: () => api.get('/auth/me'),
  registerTeacher: (payload: TeacherRegisterRequest) => api.post<RegisterResponse>('/auth/register/teacher', payload),
  registerStudent: (payload: StudentRegisterRequest) => api.post<RegisterResponse>('/auth/register/student', payload),
};
