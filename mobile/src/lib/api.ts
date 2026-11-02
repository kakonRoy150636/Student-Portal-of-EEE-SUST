import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

/**
 * The single HTTP client for the portal API.
 *
 * Auth model (mirrors `backend/app/api/v1/endpoints/auth.py`):
 *  - `POST /auth/login` returns an access token in the body and sets the
 *    rotating refresh token as an HttpOnly cookie. The refresh token is never
 *    exposed to JavaScript, so `withCredentials` is required for the cookie
 *    jar to carry it back on `/auth/refresh`.
 *  - The access token lives 15 minutes, so a 401 is recoverable: refresh once,
 *    replay the original request, and only drop the session when the server
 *    actually rejects the refresh.
 *
 * The refresh token is rotated on every use and replaying a rotated token
 * revokes the whole family, so concurrent 401s are collapsed into a single
 * refresh call (`refreshInFlight`). Without that, N parallel requests would
 * each rotate the token and trip the backend's theft detection.
 */

const DEFAULT_BASE_URL = 'http://localhost:8000/api/v1';

export const API_BASE_URL = (process.env.EXPO_PUBLIC_API_BASE_URL ?? DEFAULT_BASE_URL).replace(/\/+$/, '');

let accessToken: string | null = null;
// Every explicit token change starts a new client-side auth generation; a
// refresh response from an older generation must never restore a session the
// user has already signed out of.
let authGeneration = 0;

export const setAccessToken = (token: string | null): void => {
  authGeneration += 1;
  accessToken = token;
};

type SessionExpiredListener = () => void;
const sessionExpiredListeners = new Set<SessionExpiredListener>();

/** Notified once when the server rejects a refresh; used to bounce to login. */
export const onSessionExpired = (listener: SessionExpiredListener): (() => void) => {
  sessionExpiredListeners.add(listener);
  return () => {
    sessionExpiredListeners.delete(listener);
  };
};

const notifySessionExpired = (): void => {
  accessToken = null;
  sessionExpiredListeners.forEach((listener) => listener());
};

export const api = axios.create({
  baseURL: API_BASE_URL,
  // The refresh token cookie is path-scoped to /api/v1/auth and HttpOnly;
  // native cookie jars only accept it when credentials are requested.
  withCredentials: true,
  timeout: 15000,
  headers: { Accept: 'application/json' },
});

api.interceptors.request.use((config) => {
  (config as RetriableConfig)._authGeneration = authGeneration;
  if (accessToken) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

interface RetriableConfig extends InternalAxiosRequestConfig {
  _retried?: boolean;
  _authGeneration?: number;
}

let refreshInFlight: Promise<string> | null = null;

/**
 * Exchange the refresh cookie for a new access token.
 *
 * Uses a bare axios call rather than the `api` instance so a failing refresh
 * cannot recurse into this same interceptor.
 */
export const requestNewAccessToken = (): Promise<string> => {
  if (refreshInFlight) return refreshInFlight;

  const generation = authGeneration;
  refreshInFlight = axios
    .post<{ tokens?: { access_token?: string } }>(
      `${API_BASE_URL}/auth/refresh`,
      null,
      { withCredentials: true, timeout: 15000, headers: { Accept: 'application/json' } },
    )
    .then(({ data }) => {
      const nextToken = data?.tokens?.access_token;
      if (!nextToken) throw new Error('Refresh response contained no access token.');
      // A logout (or a second login) that landed mid-flight wins.
      if (generation !== authGeneration) throw new Error('Authentication session changed while refreshing.');
      accessToken = nextToken;
      return nextToken;
    })
    .finally(() => {
      refreshInFlight = null;
    });

  return refreshInFlight;
};

/** Whether a cookie-backed session can be recovered without stored credentials. */
export const refreshSession = async (): Promise<string | null> => {
  try {
    return await requestNewAccessToken();
  } catch {
    return null;
  }
};

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as RetriableConfig | undefined;
    const requestPath = config?.url ?? '';
    const isAuthRoute = requestPath.includes('/auth/');

    // Requests issued before a login/logout transition belong to the old
    // session and must never be replayed with the new user's credentials.
    if (config?._authGeneration !== undefined && config._authGeneration !== authGeneration) {
      return Promise.reject(error);
    }

    if (error.response?.status === 401 && config && !config._retried && !isAuthRoute) {
      config._retried = true;
      try {
        const nextToken = await requestNewAccessToken();
        config.headers = config.headers ?? {};
        config.headers.Authorization = `Bearer ${nextToken}`;
        return await api.request(config);
      } catch (refreshError) {
        const status = (refreshError as AxiosError).response?.status;
        // Only drop the session when the server actually rejected the refresh
        // cookie. A timeout or 502 means the API is unreachable, not that the
        // user is signed out.
        if (status === 401 || status === 403) notifySessionExpired();
        return Promise.reject(error);
      }
    }

    return Promise.reject(error);
  },
);
