import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { env } from '@/config/env';

let token: string | null = null;
// Every explicit token change starts a new client-side auth generation.  A
// refresh response from an older generation must never restore a session that
// the user has already logged out of or replaced with another login.
let authGeneration = 0;
export const setAccessToken = (newToken: string | null) => {
  authGeneration += 1;
  token = newToken;
};

export const api = axios.create({
  baseURL: env.API_BASE_URL,
  withCredentials: true
});

api.interceptors.request.use((config) => {
  config.headers = config.headers ?? {};
  if (typeof config.headers.set === 'function') config.headers.set('Cache-Control', 'no-store');
  else config.headers['Cache-Control'] = 'no-store';
  (config as RetriableConfig)._authGeneration = authGeneration;
  // Do not clobber an Authorization header the caller already set -- the
  // register flow attaches a short-lived upload token that is not the
  // session access token, and overwriting it would 401 the photo upload.
  if (token && config.headers && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// The access token is short-lived and the refresh token lives in an HttpOnly
// cookie, so a 401 is recoverable: call /auth/refresh once, replay the original
// request, and let the user reach a genuine login screen only when that fails.
const REFRESH_PATH = '/auth/refresh';

let refreshInFlight: Promise<string> | null = null;

export const requestNewAccessToken = (): Promise<string> => {
  // Collapse concurrent 401s into a single refresh call — without this, N
  // parallel requests would each rotate the token and all but one would be
  // rejected as replay, tripping the backend's theft detection.
  if (!refreshInFlight) {
    const generation = authGeneration;
    refreshInFlight = api
      .post(REFRESH_PATH)
      .then(({ data }) => {
        if (generation !== authGeneration) {
          throw new Error('Authentication session changed while refreshing.');
        }
        const newToken = data?.tokens?.access_token as string | undefined;
        if (!newToken) throw new Error('Refresh response contained no access token');
        token = newToken;
        return newToken;
      })
      .finally(() => {
        refreshInFlight = null;
      });
  }
  return refreshInFlight;
};

const clearSession = () => {
  setAccessToken(null);
  if (typeof window !== 'undefined') {
    // Bump a value AuthContext watches so it can clear the cached user too.
    window.dispatchEvent(new Event('auth:session-expired'));
  }
};

interface RetriableConfig extends InternalAxiosRequestConfig {
  _retried?: boolean;
  _authGeneration?: number;
}

api.interceptors.response.use(
  (response) => {
    const config = response.config as RetriableConfig;
    if (config._authGeneration !== undefined && config._authGeneration !== authGeneration) {
      return Promise.reject(new AxiosError(
        'Request belongs to an expired authentication session.',
        'ERR_CANCELED',
        config,
      ));
    }
    return response;
  },
  async (error: AxiosError) => {
    const config = error.config as RetriableConfig | undefined;
    // A request issued before a login/logout transition belongs to the old
    // session.  Replaying it with the new user's refresh cookie could leak an
    // old query into the new session, and a late 401 could log the new user
    // out, so stale requests are never refreshed.
    if (config?._authGeneration !== undefined && config._authGeneration !== authGeneration) {
      return Promise.reject(error);
    }
    const isAuthRoute = config?.url?.includes('/auth/');

    if (error.response?.status === 401 && config && !config._retried && !isAuthRoute) {
      config._retried = true;
      try {
        const newToken = await requestNewAccessToken();
        config.headers = config.headers ?? {};
        config.headers.Authorization = `Bearer ${newToken}`;
        return api.request(config);
      } catch (refreshError) {
        // Only drop the session when the server actually rejected the refresh
        // cookie. When the call never got an answer -- the API is restarting, a
        // proxy answered 502, the laptop just woke up -- the cookie is still
        // valid, and clearing it would log the user out over a network blip.
        const status = (refreshError as AxiosError).response?.status;
        if (status === 401 || status === 403) clearSession();
      }
    }

    return Promise.reject(error);
  }
);
