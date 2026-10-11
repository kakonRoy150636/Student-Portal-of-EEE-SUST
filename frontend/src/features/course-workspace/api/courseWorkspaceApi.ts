import { api } from '@/lib/axios';
import type {
  AnnouncementStatus,
  AnnouncementType,
  CourseAnnouncement,
  CourseAnnouncementCreatePayload,
  CourseAnnouncementFeed,
  CourseAnnouncementFeedParams,
  CourseAnnouncementReadResponse,
  CourseAnnouncementUpdatePayload,
  CourseEvent,
  CourseEventPayload,
  CourseQuestion,
  CourseQuestionAnswerPayload,
  CourseQuestionCreatePayload,
  CourseResourceUpdatePayload,
  CourseWorkspace,
  CourseWorkspaceResource,
  ResourceDownloadResponse,
} from '@/types/courseWorkspace';

const offeringBase = (offeringId: string) => `/course-offerings/${offeringId}`;

const workspaceBase = (offeringId: string, manager: boolean) =>
  manager ? offeringBase(offeringId) : `/student/course-offerings/${offeringId}`;

export const courseWorkspaceApi = {
  getWorkspace: (offeringId: string, manager: boolean, signal?: AbortSignal) =>
    api.get<CourseWorkspace>(`${workspaceBase(offeringId, manager)}/workspace`, { signal }),

  listAnnouncements: (
    offeringId: string,
    manager: boolean,
    params: CourseAnnouncementFeedParams,
    signal?: AbortSignal,
  ) => api.get<CourseAnnouncementFeed>(`${workspaceBase(offeringId, manager)}/announcements`, { params, signal }),

  getAnnouncement: (offeringId: string, announcementId: string, signal?: AbortSignal) =>
    api.get<CourseAnnouncement>(`${offeringBase(offeringId)}/announcements/${announcementId}`, { signal }),

  createAnnouncement: (offeringId: string, payload: CourseAnnouncementCreatePayload) =>
    api.post<CourseAnnouncement>(`${offeringBase(offeringId)}/announcements`, payload),

  updateAnnouncement: (
    offeringId: string,
    announcementId: string,
    payload: CourseAnnouncementUpdatePayload,
  ) => api.patch<CourseAnnouncement>(`${offeringBase(offeringId)}/announcements/${announcementId}`, payload),

  publishAnnouncement: (offeringId: string, announcementId: string) =>
    api.post<CourseAnnouncement>(`${offeringBase(offeringId)}/announcements/${announcementId}/publish`),

  archiveAnnouncement: (offeringId: string, announcementId: string) =>
    api.post<CourseAnnouncement>(`${offeringBase(offeringId)}/announcements/${announcementId}/archive`),

  pinAnnouncement: (offeringId: string, announcementId: string, pinned: boolean) =>
    api.patch<CourseAnnouncement>(`${offeringBase(offeringId)}/announcements/${announcementId}/pin`, {
      is_pinned: pinned,
    }),

  markAnnouncementRead: (announcementId: string) =>
    api.patch<CourseAnnouncementReadResponse>(`/course-announcements/${announcementId}/read`),

  listResources: (offeringId: string, signal?: AbortSignal) =>
    api.get<CourseWorkspaceResource[]>(`${offeringBase(offeringId)}/resources`, { signal }),

  createResourceUpload: (offeringId: string, payload: { file_name: string; file_size: number; mime_type: string }) =>
    api.post(`${offeringBase(offeringId)}/resources/presigned-upload`, payload),

  finalizeResource: (offeringId: string, payload: {
    file_key: string; title: string; category: string; course_code: string; file_name: string;
    file_size_bytes: number; mime_type: string;
  }) => api.post(`${offeringBase(offeringId)}/resources/finalize`, payload),

  updateResource: (offeringId: string, resourceId: string, payload: CourseResourceUpdatePayload) =>
    api.patch<CourseWorkspaceResource>(`${offeringBase(offeringId)}/resources/${resourceId}`, payload),

  listEvents: (offeringId: string, signal?: AbortSignal) =>
    api.get<CourseEvent[]>(`${offeringBase(offeringId)}/events`, { signal }),
  createEvent: (offeringId: string, payload: CourseEventPayload) =>
    api.post<CourseEvent>(`${offeringBase(offeringId)}/events`, payload),
  updateEvent: (offeringId: string, eventId: string, payload: Partial<CourseEventPayload>) =>
    api.patch<CourseEvent>(`${offeringBase(offeringId)}/events/${eventId}`, payload),
  archiveEvent: (offeringId: string, eventId: string) =>
    api.post<{ id: string; archived: boolean }>(`${offeringBase(offeringId)}/events/${eventId}/archive`),

  listQuestions: (offeringId: string, signal?: AbortSignal) =>
    api.get<CourseQuestion[]>(`${offeringBase(offeringId)}/questions`, { signal }),
  createQuestion: (offeringId: string, payload: CourseQuestionCreatePayload) =>
    api.post<CourseQuestion>(`${offeringBase(offeringId)}/questions`, payload),
  answerQuestion: (offeringId: string, questionId: string, payload: CourseQuestionAnswerPayload) =>
    api.patch<CourseQuestion>(`${offeringBase(offeringId)}/questions/${questionId}/answer`, payload),

  downloadResource: (resourceId: string) =>
    api.get<ResourceDownloadResponse>(`/resources/${resourceId}/download`),
};

export const announcementFilterValues: {
  statuses: AnnouncementStatus[];
  types: AnnouncementType[];
} = {
  statuses: ['draft', 'scheduled', 'published', 'archived'],
  types: ['general', 'class_update', 'class_cancelled', 'exam', 'assignment', 'urgent', 'resource', 'administrative'],
};
