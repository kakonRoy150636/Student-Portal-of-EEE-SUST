import React, { createContext, useContext, useState, ReactNode } from 'react';
import { User, UserRole, LoginCredentials } from '@/types/auth';
import { api, setAccessToken } from '@/lib/axios';

interface AuthContextType {
  user: User | null;
  role: UserRole | null;
  isAuthenticated: boolean;
  login: (creds: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>({
    id: "00000000-0000-0000-0000-000000000003",
    identifier: "2021338001",
    email: "kakon@student.sust.edu",
    full_name: "Kakon Chandro Roy",
    role: UserRole.STUDENT,
    is_active: true
  });

  const login = async (creds: LoginCredentials) => {
    const { data } = await api.post('/auth/login', creds);
    setAccessToken(data.tokens.access_token);
    setUser(data.user);
  };

  const logout = async () => {
    try { await api.post('/auth/logout'); } finally {
      setAccessToken(null);
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider value={{ user, role: user?.role ?? null, isAuthenticated: !!user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be in AuthProvider");
  return ctx;
};
