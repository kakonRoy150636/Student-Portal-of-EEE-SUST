import { afterEach, describe, expect, it } from 'vitest';
import type { AxiosResponse } from 'axios';
import { api, setAccessToken } from '../src/lib/axios';

describe('axios authentication generations', () => {
  const originalAdapter = api.defaults.adapter;

  afterEach(() => {
    api.defaults.adapter = originalAdapter;
    setAccessToken(null);
  });

  it('rejects a successful response that arrives after a session switch', async () => {
    let started!: () => void;
    const requestStarted = new Promise<void>((resolve) => { started = resolve; });
    let finish!: (response: AxiosResponse) => void;

    api.defaults.adapter = (config) => {
      started();
      return new Promise<AxiosResponse>((resolve) => {
        finish = (response) => resolve({ ...response, config });
      });
    };

    setAccessToken('old-session-token');
    const request = api.get('/private/summary');
    await requestStarted;
    setAccessToken('new-session-token');
    finish({ data: { owner: 'old-user' }, status: 200, statusText: 'OK', headers: {}, config: undefined as never });

    await expect(request).rejects.toMatchObject({ code: 'ERR_CANCELED' });
  });
});
