import { QueryClient } from '@tanstack/react-query';
import axios from 'axios';

/**
 * Shared cache. 4xx responses are not retried: a 403 will never become a 200,
 * and retrying it just delays the error state the user needs to see.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        if (axios.isAxiosError(error)) {
          const status = error.response?.status;
          if (status && status >= 400 && status < 500) return false;
        }
        return failureCount < 2;
      },
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
    mutations: { retry: false },
  },
});
