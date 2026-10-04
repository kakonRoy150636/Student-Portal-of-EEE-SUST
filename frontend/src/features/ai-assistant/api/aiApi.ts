import { api } from '@/lib/axios';

export const aiApi = {
  query: (prompt: string, course_code: string) => api.post<AIAnswer>('/ai/query', { prompt, course_code }),
};

export type AICitation = { source_id: string; chunk_id: string; document_name: string; page_number: number | null; section: string | null };
export type AIAnswer = { answer: string; citations: AICitation[]; grounded: boolean; quota_remaining: number };
