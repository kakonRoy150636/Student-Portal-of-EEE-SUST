import { api } from '@/lib/axios';
import type { ClassSchedule } from '@/types/academic';

export const scheduleApi = {
  getMyRoutine: () => api.get<ClassSchedule[]>('/schedules/my-routine'),
};
