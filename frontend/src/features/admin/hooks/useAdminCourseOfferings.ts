import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { adminApi } from '../api/adminApi';
import type {
  CourseOfferingCreatePayload,
  CourseOfferingUpdatePayload,
  TeacherAssignmentRequestFilters,
  TeacherAssignmentRequestStatus,
} from '@/types/academic';

export const adminCourseOfferingQueryKeys = {
  all: ['admin-course-offerings'] as const,
  courses: ['admin-course-offerings', 'courses'] as const,
  semesters: ['admin-course-offerings', 'semesters'] as const,
  offerings: ['admin-course-offerings', 'offerings'] as const,
  assignmentRequests: ['admin-course-offerings', 'assignment-requests'] as const,
  assignmentRequestList: (status?: TeacherAssignmentRequestStatus) =>
    ['admin-course-offerings', 'assignment-requests', 'list', status ?? null] as const,
};

type AssignmentRequestFilter = TeacherAssignmentRequestFilters | TeacherAssignmentRequestStatus;

function requestStatus(filter?: AssignmentRequestFilter): TeacherAssignmentRequestStatus | undefined {
  return typeof filter === 'string' ? filter : filter?.status;
}

function requestFilters(filter?: AssignmentRequestFilter): TeacherAssignmentRequestFilters {
  return typeof filter === 'string' ? { status: filter } : filter ?? {};
}

export function useAdminCourseOfferings() {
  return useQuery({
    queryKey: adminCourseOfferingQueryKeys.offerings,
    queryFn: async ({ signal }) => (await adminApi.listOfferings(signal)).data,
    retry: false,
  });
}

export function useAdminCourses() {
  return useQuery({
    queryKey: adminCourseOfferingQueryKeys.courses,
    queryFn: async ({ signal }) => (await adminApi.listCourses(signal)).data,
    retry: false,
  });
}

export function useAdminSemesters() {
  return useQuery({
    queryKey: adminCourseOfferingQueryKeys.semesters,
    queryFn: async ({ signal }) => (await adminApi.listActiveSemesters(signal)).data,
    retry: false,
  });
}

export function useAdminAssignmentRequests(filter?: AssignmentRequestFilter) {
  const status = requestStatus(filter);
  const filters = requestFilters(filter);

  return useQuery({
    queryKey: adminCourseOfferingQueryKeys.assignmentRequestList(status),
    queryFn: async ({ signal }) => (await adminApi.listAssignmentRequests(filters, signal)).data,
    retry: false,
  });
}

export function useCreateCourseOffering() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: CourseOfferingCreatePayload) =>
      (await adminApi.createOffering(payload)).data,
    retry: false,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: adminCourseOfferingQueryKeys.offerings });
    },
  });
}

export interface UpdateCourseOfferingVariables {
  offeringId: string;
  data: CourseOfferingUpdatePayload;
}

export function useUpdateCourseOffering() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ offeringId, data }: UpdateCourseOfferingVariables) =>
      (await adminApi.updateOffering(offeringId, data)).data,
    retry: false,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: adminCourseOfferingQueryKeys.offerings });
    },
  });
}

export function usePublishCourseOffering() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (offeringId: string) => (await adminApi.publishOffering(offeringId)).data,
    retry: false,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: adminCourseOfferingQueryKeys.offerings });
    },
  });
}

export function useUnpublishCourseOffering() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (offeringId: string) => (await adminApi.unpublishOffering(offeringId)).data,
    retry: false,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: adminCourseOfferingQueryKeys.offerings });
    },
  });
}

export function useApproveAssignmentRequest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (requestId: string) =>
      (await adminApi.approveAssignmentRequest(requestId)).data,
    retry: false,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: adminCourseOfferingQueryKeys.offerings }),
        queryClient.invalidateQueries({ queryKey: adminCourseOfferingQueryKeys.assignmentRequests }),
      ]);
    },
  });
}

export interface RejectAssignmentRequestVariables {
  requestId: string;
  rejectionReason?: string | null;
}

export function useRejectAssignmentRequest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ requestId, rejectionReason }: RejectAssignmentRequestVariables) =>
      (await adminApi.rejectAssignmentRequest(requestId, rejectionReason)).data,
    retry: false,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: adminCourseOfferingQueryKeys.offerings }),
        queryClient.invalidateQueries({ queryKey: adminCourseOfferingQueryKeys.assignmentRequests }),
      ]);
    },
  });
}
