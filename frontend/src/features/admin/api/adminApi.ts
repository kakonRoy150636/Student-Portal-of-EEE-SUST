import { api } from '@/lib/axios';

export const adminApi = {
  getStats: () => api.get('/admin/stats'),
};
