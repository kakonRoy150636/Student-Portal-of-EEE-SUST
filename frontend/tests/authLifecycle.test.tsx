import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, render, screen, waitFor } from '@testing-library/react';
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

function Probe() {
  const { user, logout } = useAuth();
  return (
    <>
      <p>{user?.id ?? 'signed-out'}</p>
      <button type="button" onClick={() => void logout()}>Logout</button>
    </>
  );
}

function renderAuth() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <AuthProvider><Probe /></AuthProvider>
    </QueryClientProvider>,
  );
}

describe('authentication lifecycle races', () => {
  beforeEach(() => {
    mocks.get.mockReset();
    mocks.post.mockReset().mockResolvedValue({ data: {} });
    mocks.setAccessToken.mockReset();
    mocks.disablePushDevice.mockReset().mockResolvedValue(undefined);
    mocks.clearRoutine.mockReset().mockResolvedValue(undefined);
    mocks.selectRoutineOwner.mockReset().mockResolvedValue(undefined);
  });

  afterEach(() => cleanup());

  it('does not restore the bootstrap session after logout wins the race', async () => {
    let finishRefresh!: () => void;
    mocks.requestNewAccessToken.mockImplementationOnce(() => new Promise<void>((resolve) => {
      finishRefresh = resolve;
    }));
    mocks.get.mockResolvedValue({ data: { id: 'old-user', role: 'student' } });

    renderAuth();
    await waitFor(() => expect(finishRefresh).toBeTypeOf('function'));

    await act(async () => {
      screen.getByRole('button', { name: 'Logout' }).click();
      await Promise.resolve();
    });
    expect(screen.getByText('signed-out')).toBeTruthy();

    await act(async () => { finishRefresh(); });
    await waitFor(() => expect(mocks.get).not.toHaveBeenCalled());
    expect(screen.getByText('signed-out')).toBeTruthy();
  });
});
