import { api } from '@/lib/axios';
import { LoginCredentials, MfaSetup, SessionSummary } from '@/types/auth';

export const authApi = {
  login: (creds: LoginCredentials) => api.post('/auth/login', creds),
  logout: () => api.post('/auth/logout'),
  me: () => api.get('/auth/me'),
  pendingApprovals: () => api.get('/auth/admin/pending-approvals'),
  approveUser: (userId: string) => api.patch(`/auth/admin/approve/${userId}`),

  // --- account security -----------------------------------------------------
  changePassword: (currentPassword: string, newPassword: string) =>
    api.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    }),
  startMfaSetup: () => api.post<MfaSetup>('/auth/mfa/setup'),
  enableMfa: (code: string) => api.post('/auth/mfa/enable', { code }),
  disableMfa: (password: string) => api.post('/auth/mfa/disable', { password }),
  verifyMfa: (mfaToken: string, code: string) =>
    api.post('/auth/mfa/verify', { mfa_token: mfaToken, code }),

  // --- password reset -------------------------------------------------------
  requestPasswordReset: (email: string) =>
    api.post('/auth/password-reset/request', { email }),
  confirmPasswordReset: (token: string, newPassword: string) =>
    api.post('/auth/password-reset/confirm', { token, new_password: newPassword }),

  // --- sessions -------------------------------------------------------------
  sessions: () => api.get<SessionSummary[]>('/auth/sessions'),
  revokeSession: (familyId: string) => api.delete(`/auth/sessions/${familyId}`),
};
