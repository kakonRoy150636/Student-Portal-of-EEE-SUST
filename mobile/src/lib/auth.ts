import * as SecureStore from 'expo-secure-store';
import { api } from './api';
import type { AuthTokens, User } from '../types';

export async function login(email: string, password: string): Promise<{ user: User; tokens: AuthTokens }> {
  const { data } = await api.post('/api/v1/auth/login', { email, password });
  await SecureStore.setItemAsync('access_token', data.access_token);
  await SecureStore.setItemAsync('refresh_token', data.refresh_token);
  return { user: data.user, tokens: { accessToken: data.access_token, refreshToken: data.refresh_token } };
}

export async function logout() {
  await SecureStore.deleteItemAsync('access_token');
  await SecureStore.deleteItemAsync('refresh_token');
}

export async function getAccessToken() {
  return SecureStore.getItemAsync('access_token');
}
