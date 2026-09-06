import { api } from '@/lib/axios';

export const resourceApi = {
  search: (q?: string) => api.get('/resources/search', { params: { q } }),
};
