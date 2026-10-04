import { getMessaging, getToken, deleteToken, isSupported, onMessage } from 'firebase/messaging';
import { api } from './axios';
import { firebaseApp, firebaseConfigured, vapidKey } from './firebase';

let owner: string | null = null;
let generation = 0;
let pending: Promise<unknown> = Promise.resolve();
let deviceId: string | null = null;
const DEVICE_KEY = 'portal-push-device';
const DISABLED_KEY = 'portal-push-disabled';
export function pushOptedOut() {
  try { return localStorage.getItem(DISABLED_KEY) === 'true'; } catch { return false; }
}
export function setPushOptOut(disabled: boolean) {
  try { if (disabled) localStorage.setItem(DISABLED_KEY, 'true'); else localStorage.removeItem(DISABLED_KEY); } catch { /* Disabled storage. */ }
}

export function activatePushUser(userId: string) {
  if (owner !== userId) { owner = userId; generation += 1; }
}
export const pushSessionRevision = () => generation;
export const pushSessionMatches = (userId: string, revision: number) => owner === userId && generation === revision;

async function pushRegistration(): Promise<ServiceWorkerRegistration> {
  let timeout: ReturnType<typeof setTimeout>;
  try {
    return await Promise.race([navigator.serviceWorker.ready,
      new Promise<never>((_, reject) => { timeout = setTimeout(() => reject(new Error('Service worker not ready')), 10000); })]);
  } finally { clearTimeout(timeout!); }
}

export function isIOS() {
  return /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
}
export function isInstalled() {
  return window.matchMedia('(display-mode: standalone)').matches ||
    Boolean((navigator as Navigator & { standalone?: boolean }).standalone);
}

export async function pushSupported() {
  return firebaseConfigured && window.isSecureContext && 'Notification' in window &&
    (!isIOS() || isInstalled()) && await isSupported();
}

function serialized<T>(work: () => Promise<T>): Promise<T> {
  const next = pending.catch(() => undefined).then(work);
  pending = next;
  return next;
}

export function refreshPushDevice(userId: string) {
  const revision = generation;
  return serialized(async () => {
    if (owner !== userId || generation !== revision || pushOptedOut() || !await pushSupported() || Notification.permission !== 'granted') return false;
    const registration = await pushRegistration();
    const token = await getToken(getMessaging(firebaseApp()), { vapidKey, serviceWorkerRegistration: registration });
    if (!token || owner !== userId || generation !== revision) return false;
    const { data } = await api.post<{ device_id: string }>('/notifications/devices/register', { fcm_token: token, platform: 'web' });
    deviceId = data.device_id;
    try { localStorage.setItem(DEVICE_KEY, deviceId); } catch { /* Optional persistence. */ }
    return true;
  });
}

/** Invalidate pending registrations before clearing the authenticated session. */
export function disablePushDevice(unregister = true) {
  generation += 1;
  owner = null;
  return serialized(async () => {
    try { deviceId ??= localStorage.getItem(DEVICE_KEY); } catch { /* Disabled storage. */ }
    try {
      if (unregister && deviceId) await api.delete(`/notifications/devices/${deviceId}`);
    } finally {
      deviceId = null;
      try { localStorage.removeItem(DEVICE_KEY); } catch { /* Disabled storage. */ }
      if (firebaseConfigured && await isSupported()) await deleteToken(getMessaging(firebaseApp()));
    }
  });
}

export async function listenToPush(onUpdate: () => void) {
  if (!await pushSupported()) return () => {};
  return onMessage(getMessaging(firebaseApp()), () => onUpdate());
}
