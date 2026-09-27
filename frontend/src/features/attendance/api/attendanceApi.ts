import { api } from '@/lib/axios';
import type { AttendanceSummary } from '@/types/academic';

export const attendanceApi = {
  getMySummary: () => api.get<AttendanceSummary>('/attendance/my-summary'),
};
