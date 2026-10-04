import React from 'react';
import { beforeEach, afterEach, it, expect, vi } from 'vitest';
import { renderHook, act, waitFor, cleanup } from '@testing-library/react';

const mocks = vi.hoisted(() => ({ user: { id: 'user-a' } as { id: string } | null,
  token: vi.fn(), removeToken: vi.fn(), post: vi.fn(), removeDevice: vi.fn() }));
vi.mock('@/contexts/AuthContext', () => ({ useAuth: () => ({ user: mocks.user }) }));
vi.mock('@/lib/firebase', () => ({ firebaseConfigured: true, firebaseApp: () => ({}), vapidKey: 'public-vapid' }));
vi.mock('firebase/messaging', () => ({ getMessaging: () => ({}), getToken: mocks.token,
  deleteToken: mocks.removeToken, isSupported: async () => true, onMessage: () => () => {} }));
vi.mock('@/lib/axios', () => ({ api: { post: mocks.post, delete: mocks.removeDevice } }));
import { usePushNotifications } from '../src/hooks/usePushNotifications';
import { activatePushUser, refreshPushDevice, disablePushDevice, isIOS, pushSupported } from '../src/lib/pushSession';

let permission = 'default';
const request = vi.fn(async () => { permission = 'granted'; return permission; });
beforeEach(() => {
  localStorage.clear(); permission = 'default'; mocks.user = { id: 'user-a' };
  mocks.token.mockReset().mockResolvedValue('fcm-token'); mocks.post.mockReset().mockResolvedValue({ data: { device_id: 'device-id' } });
  mocks.removeDevice.mockReset().mockResolvedValue({}); mocks.removeToken.mockReset().mockResolvedValue(true); request.mockClear();
  vi.stubGlobal('Notification', { get permission() { return permission; }, requestPermission: request });
  vi.stubGlobal('isSecureContext', true);
  vi.stubGlobal('matchMedia', () => ({ matches: false }));
  Object.defineProperty(navigator, 'serviceWorker', { configurable: true, value: { ready: Promise.resolve({ scope: '/' }) } });
});
afterEach(async () => { cleanup(); await disablePushDevice(); vi.unstubAllGlobals(); });

it('does not prompt at page load; user Enable action registers then logout removes token', async () => {
  const { result } = renderHook(() => usePushNotifications());
  await waitFor(() => expect(result.current.supported).toBe(true));
  expect(request).not.toHaveBeenCalled(); expect(mocks.post).not.toHaveBeenCalled();
  await act(() => result.current.enable());
  expect(request).toHaveBeenCalledOnce();
  expect(mocks.post).toHaveBeenCalledWith('/notifications/devices/register', { fcm_token: 'fcm-token', platform: 'web' });
  expect(result.current.enabled).toBe(true);
  await act(() => result.current.disable());
  expect(mocks.removeDevice).toHaveBeenCalledWith('/notifications/devices/device-id');
  expect(mocks.removeToken).toHaveBeenCalled();
  await refreshPushDevice('user-a');
  expect(mocks.post).toHaveBeenCalledTimes(1); // device opt-out persists
});

it('refreshes an already-consented token on authenticated app open without prompting', async () => {
  permission = 'granted';
  const { result } = renderHook(() => usePushNotifications());
  await waitFor(() => expect(result.current.enabled).toBe(true));
  expect(request).not.toHaveBeenCalled();
  expect(mocks.post).toHaveBeenCalledOnce();
});

it('does not prompt or register for a signed-out visitor', async () => {
  mocks.user = null;
  const { result } = renderHook(() => usePushNotifications());
  await act(() => result.current.enable());
  expect(request).not.toHaveBeenCalled(); expect(mocks.post).not.toHaveBeenCalled();
});

it('permission denial leaves the backend untouched and explains browser settings', async () => {
  request.mockImplementationOnce(async () => 'denied');
  const { result } = renderHook(() => usePushNotifications());
  await waitFor(() => expect(result.current.supported).toBe(true));
  await act(() => result.current.enable());
  expect(result.current.error).toContain('blocked'); expect(mocks.post).not.toHaveBeenCalled();
});

it('cancels a registration racing with logout', async () => {
  permission = 'granted';
  let resolve!: (token: string) => void;
  mocks.token.mockImplementationOnce(() => new Promise<string>((done) => { resolve = done; }));
  activatePushUser('race');
  const refresh = refreshPushDevice('race');
  await waitFor(() => expect(resolve).toBeTypeOf('function'));
  const logout = disablePushDevice();
  resolve('late-token');
  await refresh; await logout;
  expect(mocks.post).not.toHaveBeenCalled();
});

it('iPhone push is unavailable outside a Home Screen app', async () => {
  Object.defineProperty(navigator, 'userAgent', { configurable: true, value: 'iPhone' });
  expect(isIOS()).toBe(true); expect(await pushSupported()).toBe(false);
  vi.stubGlobal('matchMedia', () => ({ matches: true }));
  expect(await pushSupported()).toBe(true);
  Object.defineProperty(navigator, 'userAgent', { configurable: true, value: 'jsdom' });
});

it('ignores permission approval returned after logout', async () => {
  let approve!: (value: string) => void;
  request.mockImplementationOnce(() => new Promise<string>((resolve) => { approve = resolve; }));
  const { result } = renderHook(() => usePushNotifications());
  await waitFor(() => expect(result.current.supported).toBe(true));
  let enabling!: Promise<void>;
  act(() => { enabling = result.current.enable(); });
  await disablePushDevice();
  await act(async () => { permission = 'granted'; approve('granted'); await enabling; });
  expect(mocks.post).not.toHaveBeenCalled();
});
