import axios from 'axios';
import { env } from '@/config/env';

let token: string | null = null;
export const setAccessToken = (newToken: string | null) => { token = newToken; };

export const api = axios.create({
  baseURL: env.API_BASE_URL,
  withCredentials: true
});

api.interceptors.request.use((config) => {
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
