import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { env } from '@/config/env';

// The access token lives in a module-level variable only. It is never written
// to localStorage, sessionStorage or a readable cookie, so an XSS payload
// cannot lift a session out of storage; it would have to run inside this page
// and use the API as the user, which the CSP and the HttpOnly refresh cookie
// limit in duration and scope. A page reload simply performs one silent
// /auth/refresh against the cookie.
let token: string | null = null;
export const setAccessToken = (newToken: string | null) => { token = newToken; };

export const api = axios.create({
  baseURL: env.API_BASE_URL,
  withCredentials: true
});

api.interceptors.request.use((config) => {
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

// These routes either establish the session (so a refresh would be circular)
// or are the refresh call itself (retrying it is what trips replay detection).
const NO_RETRY_PREFIXES = [
  '/auth/refresh',
  '/auth/login',
  '/auth/mfa/verify',
  '/auth/password-reset',
];

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
    const url = config?.url ?? '';
    const isNoRetryRoute = NO_RETRY_PREFIXES.some((prefix) => url.includes(prefix));

    if (error.response?.status === 401 && config && !config._retried && !isNoRetryRoute) {
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

/** Restore a session from the HttpOnly refresh cookie (used on page load). */
let restoreInFlight: Promise<import('@/types/auth').User | null> | null = null;

export const restoreSession = (): Promise<import('@/types/auth').User | null> => {
  // Single-flight because React StrictMode mounts effects twice in dev: two
  // parallel refreshes would present the same rotating cookie, and the second
  // one looks exactly like a stolen-token replay to the server's family
  // revocation.
  if (!restoreInFlight) {
    restoreInFlight = api
      .post(REFRESH_PATH)
      .then(({ data }) => {
        const restored = data?.tokens?.access_token as string | undefined;
        if (restored) token = restored;
        return (data?.user as import('@/types/auth').User) ?? null;
      })
      .finally(() => {
        restoreInFlight = null;
      });
  }
  return restoreInFlight;
};

/** Machine-readable error code from the API body, when present. */
export const errorCode = (error: unknown): string | undefined => {
  const body = (error as AxiosError<{ code?: string }>)?.response?.data;
  return body?.code;
};
