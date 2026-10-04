import { describe, it, expect } from 'vitest';
import { pushUrl } from '../src/lib/pushUrl';
describe('push navigation', () => {
  it('opens the routine page and its query string', () => {
    expect(pushUrl('/schedule?day=Monday', 'https://portal.test')).toBe('/schedule?day=Monday');
  });
  it.each(['https://other.test/schedule', '//other.test/schedule', 'javascript:alert(1)', '/api/auth/logout', '/unknown'])('rejects unsafe destination %s', (url) => {
    expect(pushUrl(url, 'https://portal.test')).toBe('/notifications');
  });
});
