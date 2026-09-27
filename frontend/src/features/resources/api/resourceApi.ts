import { api } from '@/lib/axios';
import type { AcademicResource } from '@/types/academic';

export const resourceApi = {
  search: (q?: string) => api.get<AcademicResource[]>('/resources/search', { params: { q } }),
};
