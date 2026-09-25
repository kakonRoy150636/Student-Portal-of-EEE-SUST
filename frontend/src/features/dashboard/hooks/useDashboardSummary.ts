import { useQuery } from '@tanstack/react-query';
import { dashboardApi } from '@/features/dashboard/api/dashboardApi';

/**
 * Live counters for the post-login homepage.
 *
 * `retry: false` matters here: a 500 from the summary must not spin three
 * times and delay the homepage, and a degraded dashboard is still useful
 * (tiles fall back to their empty state) whereas a blank page is not.
 */
export const useDashboardSummary = () =>
  useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: async () => (await dashboardApi.getSummary()).data,
    retry: false,
    // Keep the previous numbers on screen while refetching, so a background
    // refresh does not flash the whole homepage back to a loading state.
    placeholderData: (previous) => previous,
  });
