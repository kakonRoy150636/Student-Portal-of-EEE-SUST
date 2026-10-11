import { describe, it, expect } from 'vitest';
import { pushUrl } from '../src/lib/pushUrl';
describe('push navigation', () => {
  it('opens the routine page and its query string', () => {
    expect(pushUrl('/schedule?day=Monday', 'https://portal.test')).toBe('/schedule?day=Monday');
  });
  it('allows scoped course workspace notification links only', () => {
    expect(pushUrl('/course-offerings/offering-1/workspace?announcement_id=announcement-1', 'https://portal.test')).toBe('/course-offerings/offering-1/workspace?announcement_id=announcement-1');
    expect(pushUrl('/student/courses/offering-1?tab=announcements', 'https://portal.test')).toBe('/student/courses/offering-1?tab=announcements');
    expect(pushUrl('/course-offerings/<script>/workspace', 'https://portal.test')).toBe('/notifications');
  });
  it.each(['https://other.test/schedule', '//other.test/schedule', 'javascript:alert(1)', '/api/auth/logout', '/unknown'])('rejects unsafe destination %s', (url) => {
    expect(pushUrl(url, 'https://portal.test')).toBe('/notifications');
  });
});
