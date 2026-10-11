import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/contexts/AuthContext';
import { UserRole } from '@/types/auth';
import type {
  AnnouncementAudience,
  AnnouncementStatus,
  AnnouncementType,
  CourseAnnouncementCreatePayload,
  CourseAnnouncementFeedParams,
  CourseAnnouncementUpdatePayload,
  CourseEventPayload,
  CourseQuestionAnswerPayload,
  CourseQuestionCreatePayload,
} from '@/types/courseWorkspace';
import { courseWorkspaceApi } from '../api/courseWorkspaceApi';

export const courseWorkspaceQueryKeys = {
  all: ['course-workspace'] as const,
  detail: (offeringId: string, manager: boolean) => ['course-workspace', 'detail', offeringId, manager ? 'manager' : 'learner'] as const,
  announcements: (offeringId: string, manager: boolean, params: CourseAnnouncementFeedParams) => [
    'course-workspace', 'announcements', offeringId, manager ? 'manager' : 'learner', params,
  ] as const,
  resources: (offeringId: string) => ['course-workspace', 'resources', offeringId] as const,
  events: (offeringId: string) => ['course-workspace', 'events', offeringId] as const,
  questions: (offeringId: string) => ['course-workspace', 'questions', offeringId] as const,
};

export function isWorkspaceManager(role: UserRole | null): boolean {
  return role === UserRole.TEACHER || role === UserRole.SUPER_ADMIN;
}

export function isWorkspaceLearner(role: UserRole | null): boolean {
  return role === UserRole.STUDENT || role === UserRole.CR;
}

export function useCourseWorkspace(offeringId: string | undefined) {
  const { role, user } = useAuth();
  const effectiveRole = role ?? user?.role ?? null;
  const manager = isWorkspaceManager(effectiveRole);
  const allowed = manager || isWorkspaceLearner(effectiveRole);

  return useQuery({
    queryKey: courseWorkspaceQueryKeys.detail(offeringId ?? '', manager),
    enabled: Boolean(offeringId && allowed),
    retry: false,
    queryFn: async ({ signal }) => {
      if (!offeringId) throw new Error('A course offering is required.');
      return (await courseWorkspaceApi.getWorkspace(offeringId, manager, signal)).data;
    },
  });
}

export interface CourseAnnouncementFilters {
  search: string;
  status: AnnouncementStatus | 'all';
  announcement_type: AnnouncementType | 'all';
  audience: AnnouncementAudience | 'all';
  limit: number;
  offset: number;
}

export function useCourseAnnouncements(offeringId: string | undefined, filters: CourseAnnouncementFilters) {
  const { role, user } = useAuth();
  const effectiveRole = role ?? user?.role ?? null;
  const manager = isWorkspaceManager(effectiveRole);
  const allowed = manager || isWorkspaceLearner(effectiveRole);
  const params: CourseAnnouncementFeedParams = {
    limit: filters.limit,
    offset: filters.offset,
    ...(filters.search.trim() ? { search: filters.search.trim() } : {}),
    ...(manager && filters.status !== 'all' ? { status: filters.status } : {}),
    ...(filters.announcement_type !== 'all' ? { announcement_type: filters.announcement_type } : {}),
  };

  return useQuery({
    queryKey: courseWorkspaceQueryKeys.announcements(offeringId ?? '', manager, params),
    enabled: Boolean(offeringId && allowed),
    retry: false,
    queryFn: async ({ signal }) => {
      if (!offeringId) throw new Error('A course offering is required.');
      return (await courseWorkspaceApi.listAnnouncements(offeringId, manager, params, signal)).data;
    },
  });
}

export function useCourseResources(offeringId: string | undefined) {
  const { role, user } = useAuth();
  const effectiveRole = role ?? user?.role ?? null;
  const allowed = isWorkspaceManager(effectiveRole) || isWorkspaceLearner(effectiveRole);

  return useQuery({
    queryKey: courseWorkspaceQueryKeys.resources(offeringId ?? ''),
    enabled: Boolean(offeringId && allowed),
    retry: false,
    queryFn: async ({ signal }) => {
      if (!offeringId) throw new Error('A course offering is required.');
      return (await courseWorkspaceApi.listResources(offeringId, signal)).data;
    },
  });
}

export function useCourseEvents(offeringId: string | undefined) {
  const { role, user } = useAuth();
  const effectiveRole = role ?? user?.role ?? null;
  const allowed = isWorkspaceManager(effectiveRole) || isWorkspaceLearner(effectiveRole);
  return useQuery({
    queryKey: courseWorkspaceQueryKeys.events(offeringId ?? ''),
    enabled: Boolean(offeringId && allowed),
    retry: false,
    queryFn: async ({ signal }) => {
      if (!offeringId) throw new Error('A course offering is required.');
      return (await courseWorkspaceApi.listEvents(offeringId, signal)).data;
    },
  });
}

export function useCourseQuestions(offeringId: string | undefined) {
  const { role, user } = useAuth();
  const effectiveRole = role ?? user?.role ?? null;
  const allowed = isWorkspaceManager(effectiveRole) || isWorkspaceLearner(effectiveRole);
  return useQuery({
    queryKey: courseWorkspaceQueryKeys.questions(offeringId ?? ''),
    enabled: Boolean(offeringId && allowed),
    retry: false,
    queryFn: async ({ signal }) => {
      if (!offeringId) throw new Error('A course offering is required.');
      return (await courseWorkspaceApi.listQuestions(offeringId, signal)).data;
    },
  });
}

function invalidateWorkspace(client: ReturnType<typeof useQueryClient>, offeringId: string) {
  return Promise.all([
    client.invalidateQueries({ queryKey: courseWorkspaceQueryKeys.detail(offeringId, true) }),
    client.invalidateQueries({ queryKey: courseWorkspaceQueryKeys.detail(offeringId, false) }),
    client.invalidateQueries({ queryKey: ['course-workspace', 'announcements', offeringId] }),
    client.invalidateQueries({ queryKey: courseWorkspaceQueryKeys.events(offeringId) }),
    client.invalidateQueries({ queryKey: courseWorkspaceQueryKeys.questions(offeringId) }),
    client.invalidateQueries({ queryKey: courseWorkspaceQueryKeys.resources(offeringId) }),
  ]);
}

export function useCourseAnnouncementMutations(offeringId: string) {
  const client = useQueryClient();
  const afterMutation = async () => invalidateWorkspace(client, offeringId);

  const create = useMutation({
    mutationFn: (payload: CourseAnnouncementCreatePayload) =>
      courseWorkspaceApi.createAnnouncement(offeringId, payload).then((response) => response.data),
    retry: false,
    onSuccess: afterMutation,
  });
  const update = useMutation({
    mutationFn: ({ announcementId, payload }: { announcementId: string; payload: CourseAnnouncementUpdatePayload }) =>
      courseWorkspaceApi.updateAnnouncement(offeringId, announcementId, payload).then((response) => response.data),
    retry: false,
    onSuccess: afterMutation,
  });
  const publish = useMutation({
    mutationFn: (announcementId: string) =>
      courseWorkspaceApi.publishAnnouncement(offeringId, announcementId).then((response) => response.data),
    retry: false,
    onSuccess: afterMutation,
  });
  const archive = useMutation({
    mutationFn: (announcementId: string) =>
      courseWorkspaceApi.archiveAnnouncement(offeringId, announcementId).then((response) => response.data),
    retry: false,
    onSuccess: afterMutation,
  });
  const pin = useMutation({
    mutationFn: ({ announcementId, pinned }: { announcementId: string; pinned: boolean }) =>
      courseWorkspaceApi.pinAnnouncement(offeringId, announcementId, pinned).then((response) => response.data),
    retry: false,
    onSuccess: afterMutation,
  });
  const markRead = useMutation({
    mutationFn: (announcementId: string) =>
      courseWorkspaceApi.markAnnouncementRead(announcementId).then((response) => response.data),
    retry: false,
    onSuccess: afterMutation,
  });

  const createEvent = useMutation({
    mutationFn: (payload: CourseEventPayload) => courseWorkspaceApi.createEvent(offeringId, payload).then((response) => response.data),
    retry: false,
    onSuccess: afterMutation,
  });
  const updateEvent = useMutation({
    mutationFn: ({ eventId, payload }: { eventId: string; payload: Partial<CourseEventPayload> }) =>
      courseWorkspaceApi.updateEvent(offeringId, eventId, payload).then((response) => response.data),
    retry: false,
    onSuccess: afterMutation,
  });
  const archiveEvent = useMutation({
    mutationFn: (eventId: string) => courseWorkspaceApi.archiveEvent(offeringId, eventId).then((response) => response.data),
    retry: false,
    onSuccess: afterMutation,
  });
  const createQuestion = useMutation({
    mutationFn: (payload: CourseQuestionCreatePayload) => courseWorkspaceApi.createQuestion(offeringId, payload).then((response) => response.data),
    retry: false,
    onSuccess: afterMutation,
  });
  const answerQuestion = useMutation({
    mutationFn: ({ questionId, payload }: { questionId: string; payload: CourseQuestionAnswerPayload }) =>
      courseWorkspaceApi.answerQuestion(offeringId, questionId, payload).then((response) => response.data),
    retry: false,
    onSuccess: afterMutation,
  });

  return { create, update, publish, archive, pin, markRead, createEvent, updateEvent, archiveEvent, createQuestion, answerQuestion };
}
