import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { teacherAssignmentApi } from '../api/teacherAssignmentApi';
import type {
  TeacherAssignmentRequestFilters,
  TeacherAssignmentRequestStatus,
} from '@/types/academic';

export const teacherAssignmentQueryKeys = {
  all: ['teacher-assignment'] as const,
  available: ['teacher-assignment', 'available'] as const,
  assignmentRequests: ['teacher-assignment', 'assignment-requests'] as const,
  assignmentRequestList: (status?: TeacherAssignmentRequestStatus) =>
    ['teacher-assignment', 'assignment-requests', 'list', status ?? null] as const,
  myAssignmentRequests: ['teacher-assignment', 'assignment-requests', 'mine'] as const,
  offeringAssignmentRequests: (offeringId: string) =>
    ['teacher-assignment', 'assignment-requests', 'offering', offeringId] as const,
  roster: (offeringId: string) => ['teacher-assignment', 'roster', offeringId] as const,
};

export function useAvailableOfferings() {
  return useQuery({
    queryKey: teacherAssignmentQueryKeys.available,
    queryFn: async ({ signal }) => (await teacherAssignmentApi.getAvailableOfferings(signal)).data,
    retry: false,
  });
}

export function useAssignmentRequests(filters: TeacherAssignmentRequestFilters = {}) {
  return useQuery({
    queryKey: teacherAssignmentQueryKeys.assignmentRequestList(filters.status),
    queryFn: async ({ signal }) => (await teacherAssignmentApi.getAssignmentRequests(filters, signal)).data,
    retry: false,
  });
}

export function useMyAssignmentRequests() {
  return useQuery({
    queryKey: teacherAssignmentQueryKeys.myAssignmentRequests,
    queryFn: async ({ signal }) => (await teacherAssignmentApi.getMyAssignmentRequests(signal)).data,
    retry: false,
  });
}

export function useOfferingAssignmentRequests(offeringId: string | undefined) {
  return useQuery({
    queryKey: teacherAssignmentQueryKeys.offeringAssignmentRequests(offeringId ?? ''),
    enabled: Boolean(offeringId),
    queryFn: async ({ signal }) => {
      if (!offeringId) throw new Error('A course offering is required.');
      return (await teacherAssignmentApi.getOfferingAssignmentRequests(offeringId, signal)).data;
    },
    retry: false,
  });
}

export function useCourseRoster(offeringId: string | undefined) {
  return useQuery({
    queryKey: teacherAssignmentQueryKeys.roster(offeringId ?? ''),
    enabled: Boolean(offeringId),
    queryFn: async ({ signal }) => {
      if (!offeringId) throw new Error('A course offering is required.');
      return (await teacherAssignmentApi.getRoster(offeringId, signal)).data;
    },
    retry: false,
  });
}

export function useRequestAssignment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (offeringId: string) =>
      (await teacherAssignmentApi.requestAssignment(offeringId)).data,
    retry: false,
    onSuccess: async (_request, offeringId) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: teacherAssignmentQueryKeys.available }),
        queryClient.invalidateQueries({ queryKey: teacherAssignmentQueryKeys.assignmentRequests }),
        queryClient.invalidateQueries({
          queryKey: teacherAssignmentQueryKeys.offeringAssignmentRequests(offeringId),
        }),
      ]);
    },
  });
}
