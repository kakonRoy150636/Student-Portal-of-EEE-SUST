import { describe, expect, it } from 'vitest';
import { safeExternalUrl } from '../src/lib/externalUrl';

describe('safeExternalUrl', () => {
  it('keeps absolute HTTP(S) profile links', () => {
    expect(safeExternalUrl(' https://www.linkedin.com/in/example ')).toBe('https://www.linkedin.com/in/example');
    expect(safeExternalUrl('http://linkedin.com/in/example')).toBe('http://linkedin.com/in/example');
  });

  it.each([
    'javascript:alert(document.domain)',
    'data:text/html,<script>alert(1)</script>',
    'blob:https://portal.test/unsafe',
    '/alumni/profile/123',
    'https://user:password@example.test/profile',
    'not a URL',
  ])('rejects unsafe profile link %s', (value) => {
    expect(safeExternalUrl(value)).toBeNull();
  });
});
