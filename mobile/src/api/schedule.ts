import { api } from '../lib/api';
import type { RoutineEntry } from '../types';

export const scheduleApi = {
  /** Derived from the caller's active enrolments in the active semester. */
  getMyRoutine: () => api.get<RoutineEntry[]>('/schedules/my-routine'),
};
