import { api } from '../lib/api';
import type { AuthSessionResponse, LoginRequest, User } from '../types';

export const authApi = {
  /** `identifier` is the institutional ID (or faculty/admin handle), not an email. */
  login: (credentials: LoginRequest) => api.post<AuthSessionResponse>('/auth/login', credentials),

  /** Revokes the refresh-token family and clears the HttpOnly cookie. */
  logout: () => api.post<{ message: string }>('/auth/logout'),

  me: () => api.get<User>('/auth/me'),
};
