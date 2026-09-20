import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
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
    if (token) {
      setAccessToken(token);
      api.get('/auth/me').then(({ data }) => setUser(data)).catch(() => {
        localStorage.removeItem(TOKEN_KEY);
        setAccessToken(null);
      }).finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
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
