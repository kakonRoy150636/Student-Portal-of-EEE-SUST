import { env } from '@/config/env';

/**
 * Presigned upload URLs are executable browser destinations: fetch follows
 * redirects by default and would otherwise allow a bad response to redirect a
 * user's selected file to an unrelated origin.  The API signs against the
 * configured public object-storage endpoint, so require that exact origin.
 */
export function safePresignedUploadUrl(value: unknown, endpoint = env.S3_PUBLIC_ENDPOINT_URL): string | null {
  if (typeof value !== 'string' || !value.trim()) return null;

  try {
    const upload = new URL(value.trim());
    const expected = new URL(endpoint);
    if (upload.origin !== expected.origin) return null;
    if ((upload.protocol !== 'http:' && upload.protocol !== 'https:') || upload.username || upload.password) return null;
    return upload.href;
  } catch {
    return null;
  }
}
