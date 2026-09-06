import { api } from '@/lib/axios';

export const attendanceApi = {
  getMySummary: () => api.get('/attendance/my-summary'),
};
