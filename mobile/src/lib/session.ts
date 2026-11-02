import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';

import type { User } from '../types';

const ACCESS_TOKEN_KEY = 'portal.access_token';
const USER_KEY = 'portal.user';

/**
 * Session persistence.
 *
 * On native the access token and the last-known user live in the Keychain /
 * Keystore via expo-secure-store, which is what lets the app rehydrate without
 * a network round-trip on cold start.
 *
 * On web there is deliberately no persistence: `localStorage` is readable by
 * any script on the page, and the portal's web client keeps its access token in
 * memory for exactly that reason. The refresh token is an HttpOnly cookie, so a
 * reloaded web build still recovers a session through `/auth/refresh` without
 * ever writing a token somewhere JavaScript can read it.
 */
const isWeb = Platform.OS === 'web';

let memoryToken: string | null = null;
let memoryUser: User | null = null;

export interface StoredSession {
  accessToken: string;
  user: User | null;
}

export async function saveSession(accessToken: string, user: User): Promise<void> {
  if (isWeb) {
    memoryToken = accessToken;
    memoryUser = user;
    return;
  }
  await Promise.all([
    SecureStore.setItemAsync(ACCESS_TOKEN_KEY, accessToken),
    SecureStore.setItemAsync(USER_KEY, JSON.stringify(user)),
  ]);
}

export async function saveAccessToken(accessToken: string): Promise<void> {
  if (isWeb) {
    memoryToken = accessToken;
    return;
  }
  await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, accessToken);
}

export async function saveUser(user: User): Promise<void> {
  if (isWeb) {
    memoryUser = user;
    return;
  }
  await SecureStore.setItemAsync(USER_KEY, JSON.stringify(user));
}

export async function readSession(): Promise<StoredSession | null> {
  if (isWeb) {
    return memoryToken ? { accessToken: memoryToken, user: memoryUser } : null;
  }

  const [token, rawUser] = await Promise.all([
    SecureStore.getItemAsync(ACCESS_TOKEN_KEY),
    SecureStore.getItemAsync(USER_KEY),
  ]);
  if (!token) return null;

  let user: User | null = null;
  if (rawUser) {
    try {
      user = JSON.parse(rawUser) as User;
    } catch {
      // A malformed cached user is not fatal: /auth/me re-fetches it below.
      user = null;
    }
  }
  return { accessToken: token, user };
}

export async function clearStoredSession(): Promise<void> {
  memoryToken = null;
  memoryUser = null;
  if (isWeb) return;
  await Promise.all([
    SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY),
    SecureStore.deleteItemAsync(USER_KEY),
  ]);
}
