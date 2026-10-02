import { api } from '@/lib/axios';

export interface AICitation {
  document_title: string;
  course_code: string | null;
  snippet: string;
}

export interface AIAnswer {
  answer: string;
  citations: AICitation[];
  /** True only when a language model wrote the answer from retrieved context. */
  grounded: boolean;
  /** 'gemini' | 'extractive' | 'no-context' */
  mode: string;
  session_id: string | null;
}

export interface AIHistoryRow {
  role: string;
  content: string;
  created_at: string;
}

export const aiApi = {
  query: (prompt: string, course_code?: string) =>
    api.post<AIAnswer>('/ai/query', { prompt, course_code: course_code || undefined }),
  history: () => api.get<AIHistoryRow[]>('/ai/history'),
};
