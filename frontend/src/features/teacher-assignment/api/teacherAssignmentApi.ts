import { api } from '@/lib/axios';
import type {
  CourseOffering,
  RosterEntry,
  TeacherAssignmentRequest,
  TeacherAssignmentRequestFilters,
} from '@/types/academic';

const base = '/course-offerings';

export const teacherAssignmentApi = {
  getAvailableOfferings: (signal?: AbortSignal) =>
    api.get<CourseOffering[]>(`${base}/available`, { signal }),

  getAssignmentRequests: (
    filters: TeacherAssignmentRequestFilters = {},
    signal?: AbortSignal,
  ) => api.get<TeacherAssignmentRequest[]>(`${base}/assignment-requests`, { params: filters, signal }),

  getMyAssignmentRequests: (signal?: AbortSignal) =>
    api.get<TeacherAssignmentRequest[]>(`${base}/assignment-requests/mine`, { signal }),

  requestAssignment: (offeringId: string) =>
    api.post<TeacherAssignmentRequest>(`${base}/${offeringId}/assignment-requests`),

  getOfferingAssignmentRequests: (offeringId: string, signal?: AbortSignal) =>
    api.get<TeacherAssignmentRequest[]>(`${base}/${offeringId}/assignment-requests`, { signal }),

  getRoster: (offeringId: string, signal?: AbortSignal) =>
    api.get<RosterEntry[]>(`${base}/${offeringId}/roster`, { signal }),
};
