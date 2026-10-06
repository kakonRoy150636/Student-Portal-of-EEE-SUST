import { api } from '@/lib/axios';
import type {
  ActiveCreditTotal,
  CourseEnrollment,
  CourseOffering,
  EnrollmentSelection,
  Semester,
} from '@/types/academic';

const base = '/course-offerings';

export const courseSelectionApi = {
  getActiveSemesters: (signal?: AbortSignal) => api.get<Semester[]>(`${base}/semesters/active`, { signal }),
  getPublishedOfferings: (signal?: AbortSignal) => api.get<CourseOffering[]>(`${base}/published`, { signal }),
  getMyEnrollments: (signal?: AbortSignal) => api.get<CourseEnrollment[]>(`${base}/enrollments/me`, { signal }),
  getActiveCredits: (signal?: AbortSignal) => api.get<ActiveCreditTotal>(`${base}/enrollments/me/credits`, { signal }),
  select: (offeringId: string, selection: EnrollmentSelection = { enrollment_type: 'enrolled' }) =>
    api.post<CourseEnrollment>(`${base}/${offeringId}/enroll`, selection),
  drop: (enrollmentId: number) => api.post<CourseEnrollment>(`${base}/enrollments/${enrollmentId}/drop`),
  reselect: (enrollmentId: number, selection: EnrollmentSelection = { enrollment_type: 'enrolled' }) =>
    api.post<CourseEnrollment>(`${base}/enrollments/${enrollmentId}/reselect`, selection),
};
