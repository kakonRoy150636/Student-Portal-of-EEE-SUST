import { api } from '@/lib/axios';
import { LoginCredentials } from '@/types/auth';

export const authApi = {
  login: (creds: LoginCredentials) => api.post('/auth/login', creds),
  logout: () => api.post('/auth/logout'),
  me: () => api.get('/auth/me'),
};
