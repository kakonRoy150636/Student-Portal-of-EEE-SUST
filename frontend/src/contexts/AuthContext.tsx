import React, { createContext, useContext, useEffect, useRef, useState, ReactNode } from 'react';
import type { AxiosError } from 'axios';
import { User, UserRole, LoginCredentials } from '@/types/auth';
import { api, setAccessToken, requestNewAccessToken } from '@/lib/axios';
import { useQueryClient } from '@tanstack/react-query';
import { disablePushDevice } from '@/lib/pushSession';
import { clearRoutine, selectRoutineOwner } from '@/lib/offlineRoutine';

interface AuthContextType {
  user: User | null;
  role: UserRole | null;
  isAuthenticated: boolean;
  login: (creds: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  // Auth operations can overlap: bootstrap/refresh, an explicit login, and
  // logout can all be waiting on network or IndexedDB work.  Only the latest
  // operation may publish a user into context. Reserve its generation when
  // the action is requested, before waiting for earlier queued cleanup.
  const authOperation = useRef(0);
  const queuedAction = useRef<Promise<void>>(Promise.resolve());

  const enqueueAuthAction = <T,>(action: () => Promise<T>): Promise<T> => {
    const previous = queuedAction.current;
    const next = previous.catch(() => undefined).then(action);
    queuedAction.current = next.then(() => undefined, () => undefined);
    return next;
  };

  useEffect(() => {
    // Remove tokens left by versions that persisted bearer credentials.
    try { localStorage.removeItem('access_token'); } catch { /* Storage may be disabled. */ }
    let cancelled = false;
    // Access tokens stay in memory only. On a reload, the HttpOnly refresh
    // cookie silently restores the session without exposing a bearer token to
    // localStorage/XSS-capable scripts.
    const BOOTSTRAP_ATTEMPTS = 3;
    const operation = authOperation.current;
    const isCurrent = () => !cancelled && authOperation.current === operation;
    const bootstrap = async () => {
      for (let attempt = 0; attempt < BOOTSTRAP_ATTEMPTS; attempt += 1) {
        if (!isCurrent()) return;
        try {
          await requestNewAccessToken();
          if (!isCurrent()) return;
          const { data } = await api.get('/auth/me');
          if (!isCurrent()) return;
          await selectRoutineOwner(data.id).catch(() => {});
          if (isCurrent()) setUser(data);
          return;
        } catch (error) {
          if (!isCurrent()) return;
          const status = (error as AxiosError).response?.status;
          if (status === 401 || status === 403) {
            setAccessToken(null);
            void clearRoutine().catch(() => {});
            void disablePushDevice(false).catch(() => {});
            return;
          }
          if (attempt < BOOTSTRAP_ATTEMPTS - 1) {
            await new Promise((resolve) => setTimeout(resolve, 400 * (attempt + 1)));
          }
        }
      }
    };
    void bootstrap().finally(() => {
      if (!cancelled) setLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, []);

  // Fired by the axios interceptor when refreshing fails, so a dead session
  // drops the cached user instead of leaving a stale dashboard on screen.
  useEffect(() => {
    const onExpired = () => {
      authOperation.current += 1;
      setUser(null); queryClient.clear();
      void clearRoutine().catch(() => {});
      void disablePushDevice(false).catch(() => {});
    };
    window.addEventListener('auth:session-expired', onExpired);
    return () => window.removeEventListener('auth:session-expired', onExpired);
  }, [queryClient]);

  const login = (creds: LoginCredentials) => {
    const operation = ++authOperation.current;
    return enqueueAuthAction(async () => {
      if (authOperation.current !== operation) return;
      const { data } = await api.post('/auth/login', creds);
      if (authOperation.current !== operation) return;
      const token = data.tokens.access_token;
      setAccessToken(token);
      queryClient.clear();
      await selectRoutineOwner(data.user.id).catch(() => {});
      if (authOperation.current === operation) setUser(data.user);
    });
  };

  const logout = () => {
    const operation = ++authOperation.current;
    // Clear the in-memory session before waiting on the queue or device/API
    // cleanup. This makes the route guard fail closed during a slow logout
    // and invalidates any refresh that was already in flight.
    setAccessToken(null);
    setUser(null);
    queryClient.clear();
    return enqueueAuthAction(async () => {
      try {
        await disablePushDevice().catch(() => {});
        await api.post('/auth/logout');
      } finally {
        if (authOperation.current === operation) {
          setAccessToken(null);
          setUser(null);
          queryClient.clear();
        }
        // Even when a newer login is queued, finish deleting the old routine
        // before that login can select its owner and publish a user.
        await clearRoutine().catch(() => {});
      }
    });
  };

  return (
    <AuthContext.Provider value={{ user, role: user?.role ?? null, isAuthenticated: !!user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be in AuthProvider");
  return ctx;
};
