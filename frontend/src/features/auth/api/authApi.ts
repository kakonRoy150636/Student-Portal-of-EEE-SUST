import { api } from '@/lib/axios';
import { LoginCredentials } from '@/types/auth';

export const authApi = {
  login: (creds: LoginCredentials) => api.post('/auth/login', creds),
  logout: () => api.post('/auth/logout'),
  me: () => api.get('/auth/me'),
  pendingApprovals: () => api.get('/auth/admin/pending-approvals'),
  approveUser: (userId: string) => api.patch(`/auth/admin/approve/${userId}`),
};
