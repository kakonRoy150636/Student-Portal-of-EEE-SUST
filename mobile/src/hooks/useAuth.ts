import { create } from 'zustand';

import { authApi } from '../api/auth';
import { queryClient } from '../lib/queryClient';
import { refreshSession, setAccessToken } from '../lib/api';
import { clearStoredSession, readSession, saveSession, saveUser } from '../lib/session';
import type { User } from '../types';

/**
 * `restoring` is a distinct state on purpose: the tab navigator must not flash
 * the login screen before SecureStore has answered on cold start.
 */
export type AuthStatus = 'restoring' | 'authenticated' | 'unauthenticated';

interface AuthState {
  status: AuthStatus;
  user: User | null;
  /** False until the first restore attempt finishes; drives the splash view. */
  restored: boolean;
  signIn: (identifier: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  restore: () => Promise<void>;
  /** Called when the API rejects a refresh: drop local state, don't call logout. */
  expireSession: () => void;
}

export const useAuth = create<AuthState>((set, get) => ({
  status: 'restoring',
  user: null,
  restored: false,

  signIn: async (identifier, password) => {
    const { data } = await authApi.login({ identifier: identifier.trim(), password });
    // Any cached data belongs to whoever was signed in before.
    queryClient.clear();
    setAccessToken(data.tokens.access_token);
    await saveSession(data.tokens.access_token, data.user);
    set({ status: 'authenticated', user: data.user, restored: true });
  },

  signOut: async () => {
    try {
      // Revokes the refresh-token family server-side and clears the cookie.
      await authApi.logout();
    } catch {
      // Offline sign-out still has to clear the device: leaving a token behind
      // would let the next launch restore the session the user just ended.
    }
    await clearStoredSession();
    setAccessToken(null);
    queryClient.clear();
    set({ status: 'unauthenticated', user: null, restored: true });
  },

  restore: async () => {
    if (get().restored) return;
    set({ status: 'restoring' });

    let stored = null;
    try {
      stored = await readSession();
    } catch {
      // Keychain/Keystore unavailable: fall through to a cookie-based refresh.
      stored = null;
    }

    if (stored) {
      setAccessToken(stored.accessToken);
      if (stored.user) set({ user: stored.user });

      try {
        const { data: user } = await authApi.me();
        await saveUser(user);
        set({ status: 'authenticated', user, restored: true });
        return;
      } catch (error) {
        if (!isAuthFailure(error)) {
          // A flaky network must not sign the user out; the cached profile
          // stays usable and the next request will refresh normally.
          if (stored.user) {
            set({ status: 'authenticated', user: stored.user, restored: true });
            return;
          }
        }
      }
    }

    // No usable stored session. On web this is the normal path after a reload:
    // the HttpOnly refresh cookie may still be valid.
    const refreshed = await refreshSession();
    if (refreshed) {
      try {
        const { data: user } = await authApi.me();
        await saveSession(refreshed, user);
        set({ status: 'authenticated', user, restored: true });
        return;
      } catch {
        // fall through to signed out
      }
    }

    await clearStoredSession().catch(() => undefined);
    setAccessToken(null);
    set({ status: 'unauthenticated', user: null, restored: true });
  },

  expireSession: () => {
    void clearStoredSession().catch(() => undefined);
    queryClient.clear();
    set({ status: 'unauthenticated', user: null, restored: true });
  },
}));

function isAuthFailure(error: unknown): boolean {
  const status = (error as { response?: { status?: number } })?.response?.status;
  return status === 401 || status === 403;
}
