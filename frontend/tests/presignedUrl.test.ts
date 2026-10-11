import { describe, expect, it } from 'vitest';
import { safePresignedUploadUrl } from '../src/lib/presignedUrl';

describe('safePresignedUploadUrl', () => {
  const endpoint = 'https://storage.example.test';

  it('accepts a URL signed for the configured storage origin', () => {
    expect(safePresignedUploadUrl(
      'https://storage.example.test/bucket/avatars/key.jpg?X-Amz-Signature=redacted',
      endpoint,
    )).toBe('https://storage.example.test/bucket/avatars/key.jpg?X-Amz-Signature=redacted');
  });

  it.each([
    'https://attacker.example.test/collect',
    'javascript:alert(1)',
    'data:text/plain,leak',
    'https://user:password@storage.example.test/bucket/key',
  ])('rejects an upload destination outside the configured origin: %s', (value) => {
    expect(safePresignedUploadUrl(value, endpoint)).toBeNull();
  });
});
