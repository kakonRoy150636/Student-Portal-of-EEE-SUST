import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
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

// The access token is short-lived and the refresh token lives in an HttpOnly
// cookie, so a 401 is recoverable: call /auth/refresh once, replay the original
// request, and let the user reach a genuine login screen only when that fails.
const REFRESH_PATH = '/auth/refresh';

let refreshInFlight: Promise<string> | null = null;

const requestNewAccessToken = (): Promise<string> => {
  // Collapse concurrent 401s into a single refresh call — without this, N
  // parallel requests would each rotate the token and all but one would be
  // rejected as replay, tripping the backend's theft detection.
  if (!refreshInFlight) {
    refreshInFlight = api
      .post(REFRESH_PATH)
      .then(({ data }) => {
        const newToken = data?.tokens?.access_token as string | undefined;
        if (!newToken) throw new Error('Refresh response contained no access token');
        token = newToken;
        localStorage.setItem('access_token', newToken);
        return newToken;
      })
      .finally(() => {
        refreshInFlight = null;
      });
  }
  return refreshInFlight;
};

const clearSession = () => {
  token = null;
  localStorage.removeItem('access_token');
  if (typeof window !== 'undefined') {
    // Bump a value AuthContext watches so it can clear the cached user too.
    window.dispatchEvent(new Event('auth:session-expired'));
  }
};

interface RetriableConfig extends InternalAxiosRequestConfig {
  _retried?: boolean;
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as RetriableConfig | undefined;
    const isAuthRoute = config?.url?.includes('/auth/');

    if (error.response?.status === 401 && config && !config._retried && !isAuthRoute) {
      config._retried = true;
      try {
        const newToken = await requestNewAccessToken();
        config.headers = config.headers ?? {};
        config.headers.Authorization = `Bearer ${newToken}`;
        return api.request(config);
      } catch {
        clearSession();
      }
    }

    return Promise.reject(error);
  }
);
