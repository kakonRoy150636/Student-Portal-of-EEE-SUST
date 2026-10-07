import { api } from '@/lib/axios';
import type {
  AssignmentDecisionPayload,
  CourseCatalogueItem,
  CourseOffering,
  CourseOfferingCreatePayload,
  CourseOfferingUpdatePayload,
  TeacherAssignmentRequest,
  TeacherAssignmentRequestFilters,
  TeacherAssignmentRequestStatus,
  Semester,
} from '@/types/academic';

const offeringsBase = '/course-offerings';
const assignmentRequestsBase = `${offeringsBase}/assignment-requests`;

export type AdminAssignmentRequestFilter =
  | TeacherAssignmentRequestFilters
  | TeacherAssignmentRequestStatus;

const decideAssignmentRequest = (requestId: string, payload: AssignmentDecisionPayload) =>
  api.patch<TeacherAssignmentRequest>(`${assignmentRequestsBase}/${requestId}`, payload);

export const adminApi = {
  getStats: () => api.get('/admin/stats'),

  listCourses: (signal?: AbortSignal) =>
    api.get<CourseCatalogueItem[]>('/courses', { signal }),

  listActiveSemesters: (signal?: AbortSignal) =>
    api.get<Semester[]>(`${offeringsBase}/semesters/active`, { signal }),

  listOfferings: (signal?: AbortSignal) =>
    api.get<CourseOffering[]>(offeringsBase, { signal }),

  createOffering: (payload: CourseOfferingCreatePayload) =>
    api.post<CourseOffering>(offeringsBase, payload),

  updateOffering: (offeringId: string, payload: CourseOfferingUpdatePayload) =>
    api.patch<CourseOffering>(`${offeringsBase}/${offeringId}`, payload),

  publishOffering: (offeringId: string) =>
    api.post<CourseOffering>(`${offeringsBase}/${offeringId}/publish`),

  unpublishOffering: (offeringId: string) =>
    api.post<CourseOffering>(`${offeringsBase}/${offeringId}/unpublish`),

  listAssignmentRequests: (
    filter: AdminAssignmentRequestFilter = {},
    signal?: AbortSignal,
  ) => {
    const params: TeacherAssignmentRequestFilters =
      typeof filter === 'string' ? { status: filter } : filter;
    return api.get<TeacherAssignmentRequest[]>(assignmentRequestsBase, { params, signal });
  },

  decideAssignmentRequest,

  approveAssignmentRequest: (requestId: string) =>
    decideAssignmentRequest(requestId, { decision: 'approve' }),

  rejectAssignmentRequest: (requestId: string, rejectionReason?: string | null) => {
    const payload: AssignmentDecisionPayload = { decision: 'reject' };
    if (rejectionReason !== undefined) payload.rejection_reason = rejectionReason;
    return decideAssignmentRequest(requestId, payload);
  },
};
