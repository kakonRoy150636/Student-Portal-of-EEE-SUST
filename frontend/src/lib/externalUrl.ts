/**
 * Convert an API-provided external link into a URL that is safe to put in an
 * anchor.  React escapes the attribute value, but it does not prevent a
 * `javascript:` or `data:` URL from being executed when the link is opened.
 *
 * Alumni links are user/admin supplied data, so validate them again at the
 * rendering boundary even though the normal registration form only accepts
 * HTTP(S) values.
 */
export function safeExternalUrl(value: unknown): string | null {
  if (typeof value !== 'string' || !value.trim()) return null;

  try {
    const url = new URL(value.trim());
    if (url.protocol !== 'http:' && url.protocol !== 'https:') return null;
    // Credentials in a profile link are surprising and can make a displayed
    // link look like a trusted host while sending credentials elsewhere.
    if (url.username || url.password) return null;
    return url.href;
  } catch {
    return null;
  }
}
