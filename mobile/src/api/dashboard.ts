import { api } from '../lib/api';
import type { DashboardSummary } from '../types';

export const dashboardApi = {
  /** Role-scoped counters. Only the section matching the caller's role is set. */
  getSummary: () => api.get<DashboardSummary>('/dashboard/summary'),
};
