import axios from 'axios';

let token: string | null = null;
export const setAccessToken = (newToken: string | null) => { token = newToken; };

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  withCredentials: true
});

api.interceptors.request.use((config) => {
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
