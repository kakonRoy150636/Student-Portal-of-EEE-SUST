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

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    // Access tokens stay in memory only. On a reload, the HttpOnly refresh
    // cookie silently restores the session without exposing a bearer token to
    // localStorage/XSS-capable scripts.
    const BOOTSTRAP_ATTEMPTS = 3;
    const bootstrap = async () => {
      for (let attempt = 0; attempt < BOOTSTRAP_ATTEMPTS; attempt += 1) {
        try {
          const { data } = await api.post('/auth/refresh');
          setAccessToken(data.tokens.access_token);
          if (!cancelled) setUser(data.user);
          return;
        } catch (error) {
          const status = (error as AxiosError).response?.status;
          if (status === 401 || status === 403) {
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
    setAccessToken(token);
    setUser(data.user);
  };

  const logout = async () => {
    try { await api.post('/auth/logout'); } finally {
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
