import { beforeAll, it, expect, vi } from 'vitest';
const mocks = vi.hoisted(() => ({ background: vi.fn(), messages: vi.fn() }));
vi.mock('workbox-precaching', () => ({ precacheAndRoute: vi.fn(), cleanupOutdatedCaches: vi.fn(), matchPrecache: vi.fn() }));
vi.mock('workbox-routing', () => ({ registerRoute: vi.fn(), setCatchHandler: vi.fn() }));
vi.mock('workbox-strategies', () => ({ NetworkOnly: class {} }));
vi.mock('../src/lib/firebase', () => ({ firebaseConfigured: true, firebaseApp: () => ({}) }));
vi.mock('firebase/messaging/sw', () => ({ isSupported: async () => true, getMessaging: () => ({}), onBackgroundMessage: mocks.background }));
const handlers = new Map<string, (event: unknown) => void>();
const showNotification = vi.fn();
const openWindow = vi.fn();
const matchAll = vi.fn();
beforeAll(async () => {
  vi.stubGlobal('self', { location: { origin: 'https://portal.test' }, __WB_MANIFEST: [],
    addEventListener: (type: string, handler: (event: unknown) => void) => handlers.set(type, handler),
    clients: { matchAll, openWindow, claim: vi.fn() }, registration: { showNotification } });
  await import('../src/sw/firebase-messaging-sw');
});

it('notification click navigates/focuses an existing app using FCM data.url', async () => {
  const focus = vi.fn(); const navigate = vi.fn().mockResolvedValue({ focus });
  matchAll.mockResolvedValue([{ url: 'https://portal.test/dashboard', navigate, focus }]);
  let complete!: Promise<void>;
  handlers.get('notificationclick')!({ stopImmediatePropagation: vi.fn(), notification: {
    close: vi.fn(), data: { FCM_MSG: { data: { url: '/schedule' } } },
  }, waitUntil: (promise: Promise<void>) => { complete = promise; } });
  await complete;
  expect(navigate).toHaveBeenCalledWith('/schedule'); expect(focus).toHaveBeenCalledOnce();
});

it('notification click opens the app instead of an untrusted external URL', async () => {
  matchAll.mockResolvedValue([]);
  let complete!: Promise<void>;
  handlers.get('notificationclick')!({ stopImmediatePropagation: vi.fn(), notification: {
    close: vi.fn(), data: { url: 'https://attacker.test' },
  }, waitUntil: (promise: Promise<void>) => { complete = promise; } });
  await complete;
  expect(openWindow).toHaveBeenCalledWith('/notifications');
});

it('opens a new window if the existing client cannot be navigated', async () => {
  matchAll.mockResolvedValue([{ url: 'https://portal.test/dashboard', navigate: vi.fn().mockResolvedValue(null) }]);
  let complete!: Promise<void>;
  handlers.get('notificationclick')!({ stopImmediatePropagation: vi.fn(), notification: {
    close: vi.fn(), data: { url: '/schedule' },
  }, waitUntil: (promise: Promise<void>) => { complete = promise; } });
  await complete;
  expect(openWindow).toHaveBeenCalledWith('/schedule');
});

it('does not display a second copy of Firebase automatic notifications', async () => {
  const background = mocks.background.mock.calls[0][1];
  matchAll.mockResolvedValue([]);
  await background({ notification: { title: 'Generic update' }, data: { url: '/schedule' } });
  expect(showNotification).not.toHaveBeenCalled();
  await background({ data: { url: '/schedule', title: 'Sensitive untrusted text' } });
  expect(showNotification).toHaveBeenCalledOnce();
  expect(showNotification.mock.calls[0][0]).toBe('Portal update');
  expect(showNotification.mock.calls[0][1].data.url).toBe('/schedule');
});
