const allowedPaths = new Set(['/notifications', '/schedule', '/labs', '/dashboard', '/alumni/events']);

function isCourseWorkspacePath(pathname: string): boolean {
  const segments = pathname.split('/').filter(Boolean);
  const isSafeOfferingId = (value: string | undefined) => Boolean(value && /^[a-zA-Z0-9_-]{1,100}$/.test(value));
  return (
    (segments.length === 3 && segments[0] === 'course-offerings' && segments[2] === 'workspace' && isSafeOfferingId(segments[1]))
    || (segments.length === 3 && (segments[0] === 'teacher' || segments[0] === 'student') && segments[1] === 'courses' && isSafeOfferingId(segments[2]))
  );
}

/** Push payloads cannot open external sites or arbitrary same-origin endpoints. */
export function pushUrl(value: unknown, origin: string): string {
  try {
    const target = new URL(typeof value === 'string' ? value : '/notifications', origin);
    if (target.origin !== origin || (!allowedPaths.has(target.pathname) && !isCourseWorkspacePath(target.pathname))) return '/notifications';
    return target.pathname + target.search + target.hash;
  } catch { return '/notifications'; }
}
