import axios from 'axios';
import type { AxiosError } from 'axios';

/**
 * Turn a FastAPI error into a sentence a student can act on.
 *
 * The API answers with `{"detail": "..."}` for handled failures and with a
 * list of validation objects (`{"detail": [{msg, loc}, ...]}`) for 422s, so
 * both shapes are unwrapped here rather than being rendered as `[object Object]`.
 */
export function describeError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<unknown>;
    const status = axiosError.response?.status;

    if (!axiosError.response) {
      return 'Cannot reach the portal. Check your connection and try again.';
    }

    const detail = extractDetail(axiosError.response.data);
    if (detail) return detail;

    if (status === 401) return 'Your session has expired. Please sign in again.';
    if (status === 403) return 'Your account does not have access to this section.';
    if (status === 404) return 'That information could not be found.';
    if (status === 429) return 'Too many attempts. Please wait a moment and try again.';
    if (status && status >= 500) return 'The portal is having trouble right now. Please try again later.';
    return 'Something went wrong. Please try again.';
  }

  if (error instanceof Error && error.message) return error.message;
  return 'Something went wrong. Please try again.';
}

function extractDetail(data: unknown): string | null {
  if (!data || typeof data !== 'object') return null;
  const detail = (data as { detail?: unknown }).detail;

  if (typeof detail === 'string' && detail.trim()) return detail;

  // 422 validation errors: [{ loc: [...], msg: "..." }]
  if (Array.isArray(detail) && detail.length > 0) {
    const messages = detail
      .map((item) => (item && typeof item === 'object' ? (item as { msg?: unknown }).msg : null))
      .filter((msg): msg is string => typeof msg === 'string' && msg.trim().length > 0);
    if (messages.length > 0) return messages.join('\n');
  }

  return null;
}

/** Whether an error is an HTTP 401/403 — i.e. an authentication problem. */
export function isUnauthorized(error: unknown): boolean {
  if (!axios.isAxiosError(error)) return false;
  const status = error.response?.status;
  return status === 401 || status === 403;
}
