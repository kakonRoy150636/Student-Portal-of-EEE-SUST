import { api } from '@/lib/axios';

export const projectApi = {
  getProjects: () => api.get('/projects'),
};
