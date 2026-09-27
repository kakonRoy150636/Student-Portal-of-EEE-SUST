import { api } from '@/lib/axios';
import type { CapstoneProject } from '@/types/academic';

export const projectApi = {
  getProjects: () => api.get<CapstoneProject[]>('/projects'),
};
