import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import type { AxiosError } from 'axios';
import { User, UserRole, LoginCredentials } from '@/types/auth';
import { api, setAccessToken } from '@/lib/axios';

interface AuthContextType {
  user: User | null;
  role: UserRole | null;
  isAuthenticated: boolean;
  login: (creds: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = 'access_token';

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      setLoading(false);
      return;
    }
    setAccessToken(token);

    let cancelled = false;
    // A stale access token is normal here: the axios interceptor silently calls
    // /auth/refresh and replays this request. So a rejection means either that
    // refresh failed too (an authoritative 401 -- the session really is over)
    // or that the API could not be reached at all. The second case is what a
    // cold start or a restart looks like from the browser, and deleting the
    // token there would sign people out for no reason -- so retry a few times
    // and only clear the session on a real 401.
    const BOOTSTRAP_ATTEMPTS = 3;
    const bootstrap = async () => {
      for (let attempt = 0; attempt < BOOTSTRAP_ATTEMPTS; attempt += 1) {
        try {
          const { data } = await api.get('/auth/me');
          if (!cancelled) setUser(data);
          return;
        } catch (error) {
          const status = (error as AxiosError).response?.status;
          if (status === 401 || status === 403) {
            localStorage.removeItem(TOKEN_KEY);
            setAccessToken(null);
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
    const onExpired = () => setUser(null);
    window.addEventListener('auth:session-expired', onExpired);
    return () => window.removeEventListener('auth:session-expired', onExpired);
  }, []);

  const login = async (creds: LoginCredentials) => {
    const { data } = await api.post('/auth/login', creds);
    const token = data.tokens.access_token;
    localStorage.setItem(TOKEN_KEY, token);
    setAccessToken(token);
    setUser(data.user);
  };

  const logout = async () => {
    try { await api.post('/auth/logout'); } finally {
      localStorage.removeItem(TOKEN_KEY);
      setAccessToken(null);
      setUser(null);
    }
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
