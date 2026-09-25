import { api } from '@/lib/axios';
import type { DashboardSummary } from '@/features/dashboard/types/dashboard';

export const dashboardApi = {
  getSummary: () => api.get<DashboardSummary>('/dashboard/summary'),
};
