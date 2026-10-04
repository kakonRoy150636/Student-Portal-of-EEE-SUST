/// <reference lib="webworker" />
import { precacheAndRoute, cleanupOutdatedCaches, matchPrecache } from 'workbox-precaching';
import { registerRoute, setCatchHandler } from 'workbox-routing';
import { NetworkOnly } from 'workbox-strategies';
import { getMessaging, onBackgroundMessage, isSupported } from 'firebase/messaging/sw';
import { firebaseApp, firebaseConfigured } from '../lib/firebase';
import { pushUrl } from '../lib/pushUrl';

declare const self: ServiceWorkerGlobalScope & { __WB_MANIFEST: Array<{ url: string; revision: string | null }> };

// Install our listener before Firebase's default click handler.
self.addEventListener('notificationclick', (event) => {
  event.stopImmediatePropagation();
  event.notification.close();
  const data = event.notification.data;
  const url = pushUrl(data?.url ?? data?.FCM_MSG?.data?.url, self.location.origin);
  event.waitUntil((async () => {
    const windows = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    const existing = windows.find((client) => new URL(client.url).origin === self.location.origin) as WindowClient | undefined;
    if (existing) {
      const navigated = await existing.navigate(url);
      if (navigated) await navigated.focus();
      else await self.clients.openWindow(url);
    } else { await self.clients.openWindow(url); }
  })());
});

precacheAndRoute(self.__WB_MANIFEST);
cleanupOutdatedCaches();
// Never cache authenticated API responses. Navigation offline goes to a small
// pre-cached shell that reads only the routine snapshot, not an auth session.
registerRoute(({ request }) => request.mode === 'navigate', new NetworkOnly());
setCatchHandler(async ({ request }) => request.mode === 'navigate'
  ? (await matchPrecache('/offline.html')) ?? Response.error() : Response.error());
self.addEventListener('message', (event) => {
  if (event.data?.type === 'SKIP_WAITING') void self.skipWaiting();
});
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()));

if (firebaseConfigured) {
  void isSupported().then((supported) => {
    if (!supported) return;
    onBackgroundMessage(getMessaging(firebaseApp()), async (payload) => {
      // Notification payloads are already displayed by Firebase. Never display
      // them a second time. Data-only messages use the generic portal template.
      if (!payload.notification) {
        await self.registration.showNotification('Portal update', {
          body: 'A new update is available. Open the portal for details.',
          icon: '/icons/icon-192.png', badge: '/icons/icon-192.png',
          data: { url: pushUrl(payload.data?.url, self.location.origin) },
          tag: payload.data?.notification_id,
        });
      }
      const clients = await self.clients.matchAll({ type: 'window' });
      clients.forEach((client) => client.postMessage({ type: 'PORTAL_NOTIFICATION' }));
    });
  }).catch(() => { /* Offline/config failure must not break app-shell caching. */ });
}
