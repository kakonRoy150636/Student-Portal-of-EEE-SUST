import { api } from '../lib/api';
import type { ActiveCreditTotal, Enrollment } from '../types';

export const coursesApi = {
  /** The caller's own course enrolments; students and CRs only. */
  getMyEnrollments: () => api.get<Enrollment[]>('/course-offerings/enrollments/me'),

  /** Active (current-semester) credit load, recomputed server-side. */
  getActiveCredits: () => api.get<ActiveCreditTotal>('/course-offerings/enrollments/me/credits'),
};
