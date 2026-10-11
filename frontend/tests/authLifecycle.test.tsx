import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  requestNewAccessToken: vi.fn(),
  setAccessToken: vi.fn(),
  disablePushDevice: vi.fn(),
  clearRoutine: vi.fn(),
  selectRoutineOwner: vi.fn(),
}));

vi.mock('@/lib/axios', () => ({
  api: { get: mocks.get, post: mocks.post },
  requestNewAccessToken: mocks.requestNewAccessToken,
  setAccessToken: mocks.setAccessToken,
}));
vi.mock('@/lib/pushSession', () => ({ disablePushDevice: mocks.disablePushDevice }));
vi.mock('@/lib/offlineRoutine', () => ({
  clearRoutine: mocks.clearRoutine,
  selectRoutineOwner: mocks.selectRoutineOwner,
}));

import { AuthProvider, useAuth } from '../src/contexts/AuthContext';

const credentials = { identifier: 'student', password: 'test-password' };
const loginResponse = (id: string) => ({
  data: { user: { id, role: 'student' }, tokens: { access_token: `${id}-token` } },
});

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((done, fail) => { resolve = done; reject = fail; });
  return { promise, resolve, reject };
}

function renderAuth() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const view = renderHook(() => useAuth(), {
    wrapper: ({ children }) => (
      <QueryClientProvider client={client}>
        <AuthProvider>{children}</AuthProvider>
      </QueryClientProvider>
    ),
  });
  return { ...view, client };
}

describe('authentication lifecycle races', () => {
  beforeEach(() => {
    mocks.get.mockReset().mockResolvedValue({ data: { id: 'old-user', role: 'student' } });
    mocks.post.mockReset().mockResolvedValue({ data: {} });
    mocks.requestNewAccessToken.mockReset().mockResolvedValue('bootstrap-token');
    mocks.setAccessToken.mockReset();
    mocks.disablePushDevice.mockReset().mockResolvedValue(undefined);
    mocks.clearRoutine.mockReset().mockResolvedValue(undefined);
    mocks.selectRoutineOwner.mockReset().mockResolvedValue(undefined);
  });

  afterEach(() => cleanup());

  it('does not restore the bootstrap session after logout wins the race', async () => {
    const refresh = deferred<string>();
    mocks.requestNewAccessToken.mockReturnValueOnce(refresh.promise);
    const { result } = renderAuth();

    await act(() => result.current.logout());
    expect(result.current.isAuthenticated).toBe(false);

    await act(async () => { refresh.resolve('stale-token'); });
    expect(mocks.get).not.toHaveBeenCalled();
    expect(mocks.selectRoutineOwner).not.toHaveBeenCalled();
    expect(result.current.user).toBeNull();
    expect(result.current.loading).toBe(false);
    expect(mocks.disablePushDevice).toHaveBeenCalledOnce();
    expect(mocks.clearRoutine).toHaveBeenCalledOnce();
  });

  it.each(['success', 'failure'])('ignores a slow login %s after logout is requested', async (outcome) => {
    const loginRequest = deferred<ReturnType<typeof loginResponse>>();
    const logoutRequest = deferred<{ data: object }>();
    mocks.post.mockImplementation((url: string) => (
      url === '/auth/login' ? loginRequest.promise : logoutRequest.promise
    ));
    const { result, client } = renderAuth();
    await waitFor(() => expect(result.current.user?.id).toBe('old-user'));
    client.setQueryData(['private'], { owner: 'old-user' });

    let signingIn!: Promise<unknown>;
    act(() => { signingIn = result.current.login(credentials).catch((error: unknown) => error); });
    await waitFor(() => expect(mocks.post).toHaveBeenCalledWith('/auth/login', credentials));

    let signingOut!: Promise<void>;
    act(() => { signingOut = result.current.logout(); });
    // Cookie-changing requests must stay ordered even when local auth is invalidated.
    expect(mocks.post).not.toHaveBeenCalledWith('/auth/logout');

    await act(async () => {
      if (outcome === 'success') loginRequest.resolve(loginResponse('late-user'));
      else loginRequest.reject(new Error('Authentication session changed'));
      await signingIn;
    });
    await waitFor(() => expect(mocks.post).toHaveBeenCalledWith('/auth/logout'));
    expect(mocks.setAccessToken).not.toHaveBeenCalledWith('late-user-token');
    expect(mocks.selectRoutineOwner).not.toHaveBeenCalledWith('late-user');
    expect(result.current.user).toBeNull();
    expect(mocks.disablePushDevice).toHaveBeenCalledOnce();

    await act(async () => { logoutRequest.resolve({ data: {} }); await signingOut; });
    expect(mocks.clearRoutine).toHaveBeenCalledOnce();
    expect(mocks.setAccessToken).toHaveBeenLastCalledWith(null);
    expect(client.getQueryData(['private'])).toBeUndefined();
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('clears local auth immediately while a login is waiting for offline storage', async () => {
    const { result, client } = renderAuth();
    await waitFor(() => expect(result.current.user?.id).toBe('old-user'));
    const selection = deferred<void>();
    mocks.selectRoutineOwner.mockReturnValueOnce(selection.promise);
    mocks.post.mockResolvedValueOnce(loginResponse('late-user'));

    let signingIn!: Promise<void>;
    act(() => { signingIn = result.current.login(credentials); });
    await waitFor(() => expect(mocks.selectRoutineOwner).toHaveBeenCalledWith('late-user'));
    client.setQueryData(['private'], { owner: 'old-user' });

    let signingOut!: Promise<void>;
    act(() => { signingOut = result.current.logout(); });
    expect(result.current.user).toBeNull();
    expect(mocks.setAccessToken).toHaveBeenLastCalledWith(null);
    expect(client.getQueryData(['private'])).toBeUndefined();
    expect(mocks.post).not.toHaveBeenCalledWith('/auth/logout');

    await act(async () => { selection.resolve(); await signingIn; await signingOut; });
    expect(result.current.isAuthenticated).toBe(false);
    expect(mocks.clearRoutine).toHaveBeenCalledOnce();
  });

  it('only publishes the newest login when an earlier login is still in flight', async () => {
    const firstLogin = deferred<ReturnType<typeof loginResponse>>();
    const nextLogin = deferred<ReturnType<typeof loginResponse>>();
    mocks.post.mockReturnValueOnce(firstLogin.promise).mockReturnValueOnce(nextLogin.promise);
    const { result, client } = renderAuth();
    await waitFor(() => expect(result.current.loading).toBe(false));
    client.setQueryData(['private'], { owner: 'old-user' });

    let firstAttempt!: Promise<void>;
    act(() => { firstAttempt = result.current.login(credentials); });
    await waitFor(() => expect(mocks.post).toHaveBeenCalledTimes(1));
    let nextAttempt!: Promise<void>;
    const nextCredentials = { ...credentials, identifier: 'next-student' };
    act(() => { nextAttempt = result.current.login(nextCredentials); });

    await act(async () => { firstLogin.resolve(loginResponse('stale-user')); await firstAttempt; });
    await waitFor(() => expect(mocks.post).toHaveBeenCalledWith('/auth/login', nextCredentials));
    expect(mocks.setAccessToken).not.toHaveBeenCalledWith('stale-user-token');
    expect(mocks.selectRoutineOwner).not.toHaveBeenCalledWith('stale-user');

    await act(async () => { nextLogin.resolve(loginResponse('next-user')); await nextAttempt; });
    expect(result.current.user?.id).toBe('next-user');
    expect(mocks.setAccessToken).toHaveBeenLastCalledWith('next-user-token');
    expect(mocks.selectRoutineOwner).toHaveBeenLastCalledWith('next-user');
    expect(client.getQueryData(['private'])).toBeUndefined();
  });

  it('skips a queued login that logout supersedes before it starts', async () => {
    const { result } = renderAuth();
    await waitFor(() => expect(result.current.loading).toBe(false));
    mocks.post.mockResolvedValue(loginResponse('stale-user'));

    await act(async () => {
      const signingIn = result.current.login(credentials);
      const signingOut = result.current.logout();
      await Promise.all([signingIn, signingOut]);
    });

    expect(mocks.post).not.toHaveBeenCalledWith('/auth/login', credentials);
    expect(mocks.post).toHaveBeenCalledWith('/auth/logout');
    expect(mocks.setAccessToken).not.toHaveBeenCalledWith('stale-user-token');
    expect(result.current.user).toBeNull();
  });

  it('finishes push and offline logout cleanup before a newer login starts', async () => {
    const pushCleanup = deferred<void>();
    const routineCleanup = deferred<void>();
    const logoutRequest = deferred<{ data: object }>();
    mocks.disablePushDevice.mockReturnValueOnce(pushCleanup.promise);
    mocks.clearRoutine.mockReturnValueOnce(routineCleanup.promise);
    mocks.post.mockImplementation((url: string) => (
      url === '/auth/logout' ? logoutRequest.promise : Promise.resolve(loginResponse('next-user'))
    ));
    const { result } = renderAuth();
    await waitFor(() => expect(result.current.loading).toBe(false));

    let signingOut!: Promise<void>;
    act(() => { signingOut = result.current.logout(); });
    await waitFor(() => expect(mocks.disablePushDevice).toHaveBeenCalledOnce());
    let signingIn!: Promise<void>;
    act(() => { signingIn = result.current.login(credentials); });
    expect(mocks.post).not.toHaveBeenCalled();

    await act(async () => { pushCleanup.resolve(); });
    expect(mocks.post).toHaveBeenCalledWith('/auth/logout');
    expect(mocks.post).not.toHaveBeenCalledWith('/auth/login', credentials);

    await act(async () => { logoutRequest.resolve({ data: {} }); });
    expect(mocks.clearRoutine).toHaveBeenCalledOnce();
    expect(mocks.post).not.toHaveBeenCalledWith('/auth/login', credentials);

    await act(async () => { routineCleanup.resolve(); await signingOut; await signingIn; });
    expect(result.current.user?.id).toBe('next-user');
    expect(mocks.setAccessToken).toHaveBeenLastCalledWith('next-user-token');
    expect(mocks.selectRoutineOwner).toHaveBeenLastCalledWith('next-user');
  });
});
