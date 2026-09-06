import { api } from '@/lib/axios';

export const careerApi = {
  getOpportunities: () => api.get('/career/opportunities'),
};
