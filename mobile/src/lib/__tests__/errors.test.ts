import { describe, expect, it } from '@jest/globals';
import { AxiosError, AxiosHeaders } from 'axios';

import { describeError, isUnauthorized } from '../errors';

function axiosErrorWith(status: number | undefined, data?: unknown): AxiosError {
  if (status === undefined) {
    return new AxiosError('Network Error', 'ERR_NETWORK');
  }
  return new AxiosError('Request failed', 'ERR_BAD_RESPONSE', undefined, undefined, {
    status,
    statusText: 'error',
    data,
    headers: {},
    config: { headers: new AxiosHeaders() },
  });
}

describe('describeError', () => {
  it('surfaces a FastAPI string detail verbatim', () => {
    expect(
      describeError(axiosErrorWith(401, { detail: 'Invalid institutional identifier or password.' })),
    ).toBe('Invalid institutional identifier or password.');
  });

  it('unwraps 422 validation arrays into readable lines', () => {
    const error = axiosErrorWith(422, {
      detail: [
        { loc: ['body', 'identifier'], msg: 'String should have at least 3 characters' },
        { loc: ['body', 'password'], msg: 'String should have at least 6 characters' },
      ],
    });

    expect(describeError(error)).toBe(
      'String should have at least 3 characters\nString should have at least 6 characters',
    );
  });

  it('falls back to status-specific copy when the body carries no detail', () => {
    expect(describeError(axiosErrorWith(403, {}))).toBe('Your account does not have access to this section.');
    expect(describeError(axiosErrorWith(429, {}))).toBe('Too many attempts. Please wait a moment and try again.');
    expect(describeError(axiosErrorWith(500, {}))).toBe(
      'The portal is having trouble right now. Please try again later.',
    );
  });

  it('reports connectivity problems rather than blaming the server', () => {
    expect(describeError(axiosErrorWith(undefined))).toBe(
      'Cannot reach the portal. Check your connection and try again.',
    );
  });

  it('handles non-axios errors', () => {
    expect(describeError(new Error('boom'))).toBe('boom');
    expect(describeError('nope')).toBe('Something went wrong. Please try again.');
  });
});

describe('isUnauthorized', () => {
  it('only treats 401 and 403 as authentication failures', () => {
    expect(isUnauthorized(axiosErrorWith(401))).toBe(true);
    expect(isUnauthorized(axiosErrorWith(403))).toBe(true);
    expect(isUnauthorized(axiosErrorWith(500))).toBe(false);
    expect(isUnauthorized(axiosErrorWith(undefined))).toBe(false);
    expect(isUnauthorized(new Error('x'))).toBe(false);
  });
});
