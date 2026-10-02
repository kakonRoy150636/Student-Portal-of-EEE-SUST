import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { User, UserRole, LoginCredentials } from '@/types/auth';
import { api, restoreSession, setAccessToken } from '@/lib/axios';

/** What a login attempt resolved to. */
export interface LoginOutcome {
  mfaRequired: boolean;
  mfaToken?: string;
}

interface AuthContextType {
  user: User | null;
  role: UserRole | null;
  isAuthenticated: boolean;
  login: (creds: LoginCredentials) => Promise<LoginOutcome>;
  completeMfaLogin: (mfaToken: string, code: string) => Promise<void>;
  logout: () => Promise<void>;
  /** Re-read the account (after changing a password, enabling MFA, …). */
  refreshUser: () => Promise<void>;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    // No token is persisted anywhere, so "am I signed in?" is answered by the
    // HttpOnly refresh cookie alone. A 401 here is the normal signed-out case,
    // not an error worth retrying.
    const bootstrap = async () => {
      try {
        const restored = await restoreSession();
        if (!cancelled) setUser(restored);
      } catch {
        if (!cancelled) {
          setAccessToken(null);
          setUser(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void bootstrap();

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

  const login = async (creds: LoginCredentials): Promise<LoginOutcome> => {
    const { data } = await api.post('/auth/login', creds);
    if (data?.mfa_required) {
      // Password accepted, one-time code outstanding: still not a session.
      return { mfaRequired: true, mfaToken: data.mfa_token as string };
    }
    setAccessToken(data.tokens.access_token);
    setUser(data.user);
    return { mfaRequired: false };
  };

  const completeMfaLogin = async (mfaToken: string, code: string) => {
    const { data } = await api.post('/auth/mfa/verify', { mfa_token: mfaToken, code });
    setAccessToken(data.tokens.access_token);
    setUser(data.user);
  };

  const refreshUser = async () => {
    const { data } = await api.get('/auth/me');
    setUser(data);
  };

  const logout = async () => {
    try {
      await api.post('/auth/logout');
    } finally {
      setAccessToken(null);
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        role: user?.role ?? null,
        isAuthenticated: !!user,
        login,
        completeMfaLogin,
        logout,
        refreshUser,
        loading,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be in AuthProvider');
  return ctx;
};
