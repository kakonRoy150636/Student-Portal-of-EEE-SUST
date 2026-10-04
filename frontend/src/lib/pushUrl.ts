const allowedPaths = new Set(['/notifications', '/schedule', '/labs', '/dashboard', '/alumni/events']);

/** Push payloads cannot open external sites or arbitrary same-origin endpoints. */
export function pushUrl(value: unknown, origin: string): string {
  try {
    const target = new URL(typeof value === 'string' ? value : '/notifications', origin);
    if (target.origin !== origin || !allowedPaths.has(target.pathname)) return '/notifications';
    return target.pathname + target.search + target.hash;
  } catch { return '/notifications'; }
}
