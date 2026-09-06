import { api } from '@/lib/axios';

export const scheduleApi = {
  getMyRoutine: () => api.get('/schedules/my-routine'),
};
