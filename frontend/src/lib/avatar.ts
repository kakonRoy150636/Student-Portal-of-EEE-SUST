import { env } from '@/config/env';

/**
 * Build a browser-loadable URL for a stored avatar.
 *
 * The backend returns a storage key ("avatars/<uuid>.jpg"), not a URL, so
 * every consumer used to guess at the path -- which is why the image never
 * appeared. This is the single place that turns a key into a URL.
 *
 * Returns null when there is no key, so callers can fall back to initials.
 */
export const avatarUrl = (avatarKey?: string | null): string | null => {
  if (!avatarKey) return null;
  // Normalise defensively: a key must stay inside the avatars/ prefix, and
  // a leading slash would produce a protocol-relative URL pointing at the
  // app origin instead of object storage.
  const key = avatarKey.replace(/^\/+/, '');
  if (!key.startsWith('avatars/')) return null;
  const base = env.S3_PUBLIC_ENDPOINT_URL.replace(/\/+$/, '');
  return `${base}/${env.S3_BUCKET_NAME}/${key}`;
};

/** First letters of a name, used when there is no avatar image. */
export const initialsOf = (fullName?: string | null): string => {
  const name = (fullName || '').trim();
  if (!name) return '?';
  const parts = name.split(/\s+/).filter(Boolean);
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
};

export const MAX_AVATAR_BYTES = 10 * 1024 * 1024;

export const ACCEPTED_AVATAR_TYPES = 'image/jpeg,image/png,image/webp,image/gif';
