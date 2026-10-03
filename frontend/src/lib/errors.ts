import { isAxiosError } from 'axios';

export function getErrorMessage(error: unknown, fallback: string): string {
  if (isAxiosError<{ error?: unknown; detail?: unknown }>(error)) {
    const data = error.response?.data;
    if (typeof data?.error === 'string') return data.error;
    if (typeof data?.detail === 'string') return data.detail;
  }
  return error instanceof Error ? error.message : fallback;
}
