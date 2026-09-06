import { api } from '@/lib/axios';

export const aiApi = {
  query: (prompt: string, course_code: string) => api.post('/ai/query', { prompt, course_code }),
};
