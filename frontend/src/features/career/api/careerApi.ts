import { api } from '@/lib/axios';
import type { CareerOpportunity } from '@/types/academic';

export const careerApi = {
  getOpportunities: () => api.get<CareerOpportunity[]>('/career/opportunities'),
};
