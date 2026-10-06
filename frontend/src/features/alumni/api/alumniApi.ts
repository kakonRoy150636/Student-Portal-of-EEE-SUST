import { api } from '@/lib/axios';

export interface AlumniUserSummary {
  id: string;
  full_name: string;
  identifier: string;
  email?: string | null;
  avatar_key?: string | null;
}

export interface AlumniProfile {
  id: string;
  user_id: string;
  batch_year: number;
  department: string;
  graduation_date: string;
  current_company: string | null;
  designation: string | null;
  industry: string | null;
  linkedin_url: string | null;
  verified_by_admin: boolean;
  membership_status: 'pending' | 'active' | 'expired' | 'rejected';
  is_visible: boolean;
  current_city?: string | null;
  current_country?: string | null;
  bio?: string | null;
  phone?: string | null;
  email_visible?: boolean;
  phone_visible?: boolean;
  is_verified?: boolean;
  user?: AlumniUserSummary | null;
}

export type EmploymentSector = 'industry' | 'academia' | 'government' | 'startup' | 'higher_study' | 'other';

export interface AlumniEmployment {
  id: string;
  alumni_id: string;
  organization: string;
  position: string;
  sector: EmploymentSector;
  city: string | null;
  country: string | null;
  start_date: string | null;
  end_date: string | null;
  is_current: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface AlumniBatch { year: number; alumni_count: number; }
export interface AlumniDirectoryItem {
  id: string;
  full_name: string;
  batch_year: number;
  department: string;
  current_city: string | null;
  current_country: string | null;
  linkedin_url: string | null;
  email: string | null;
  phone: string | null;
  current_employment: AlumniEmployment | null;
}
export interface AlumniDirectoryResponse { items: AlumniDirectoryItem[]; page: number; page_size: number; total: number; pages: number; }
export interface AlumniBatchSummary {
  year: number;
  total: number;
  employed: number;
  higher_study: number;
  abroad: number;
  top_companies: { name: string; count: number }[];
  top_countries: { name: string; count: number }[];
}
export interface AlumniProfileDetail extends AlumniDirectoryItem {
  bio: string | null;
  is_verified: boolean;
  membership_status: string;
  is_visible: boolean;
  employments: AlumniEmployment[];
}

export interface AlumniNewsPost {
  id: string;
  title: string;
  slug: string;
  body: string;
  cover_photo_key: string | null;
  is_published: boolean;
  published_at: string | null;
}

export interface AlumniEvent {
  id: string;
  title: string;
  description: string;
  venue: string;
  starts_at: string;
  ends_at: string;
  event_type: 'reunion' | 'webinar' | 'meetup';
  capacity: number | null;
  is_published: boolean;
  members_only: boolean;
  attending_count: number;
}

export interface AlumniScholarship {
  id: string;
  title: string;
  description: string;
  eligibility: string;
  amount_bdt: number | null;
  deadline: string;
  application_target: string;
  is_published: boolean;
}

export interface GalleryPhoto {
  id: string;
  photo_key: string;
  caption: string | null;
  sort_order: number;
}

export interface GalleryAlbum {
  id: string;
  title: string;
  description: string | null;
  cover_photo_key: string | null;
  photos: GalleryPhoto[];
}

export interface LandingStats {
  active_alumni: number;
  published_events: number;
  open_scholarships: number;
  published_news: number;
  batches: number;
}

export interface AlumniLandingPayload {
  stats: LandingStats;
  news: AlumniNewsPost[];
  events: AlumniEvent[];
  gallery: GalleryAlbum[];
  scholarships: AlumniScholarship[];
}

export interface EventRsvp {
  id: string;
  event_id: string;
  rsvp_status: 'attending' | 'interested' | 'not_attending';
  note: string | null;
  event: AlumniEvent | null;
}

export interface ScholarshipApplication {
  id: string;
  scholarship_id: string;
  status: string;
  created_at: string;
  scholarship: AlumniScholarship | null;
}

export interface MentorshipPair {
  id: string;
  mentor_id: string;
  mentee_id: string;
  status: string;
  mentee_note: string | null;
  mentor_note: string | null;
  mentor?: AlumniUserSummary | null;
  mentee?: AlumniUserSummary | null;
}

export interface AlumniDashboardPayload {
  profile: AlumniProfile | null;
  events: EventRsvp[];
  applications: ScholarshipApplication[];
  mentorship: MentorshipPair[];
  pending_verification: boolean;
}

export interface DirectoryQuery {
  q?: string;
  batch_year?: number;
  industry?: string;
}

export interface StandaloneDirectoryQuery {
  batch?: number;
  company?: string;
  country?: string;
  sector?: EmploymentSector;
  q?: string;
  page?: number;
  page_size?: number;
}

export interface AlumniClaimInput {
  batch_year: number;
  department: string;
  graduation_date: string;
  current_company?: string | null;
  designation?: string | null;
  industry?: string | null;
  linkedin_url?: string | null;
  is_visible?: boolean;
  current_city?: string | null;
  current_country?: string | null;
  bio?: string | null;
  phone?: string | null;
  email_visible?: boolean;
  phone_visible?: boolean;
}

export interface AlumniRegisterInput extends AlumniClaimInput {
  full_name: string;
  email: string;
  password: string;
}

export interface RegisterResult {
  message: string;
  requires_approval: boolean;
  upload_token: string;
}

/**
 * Every path below maps 1:1 to a route in backend/app/api/v1/endpoints/alumni.py.
 * Domain errors from that module render as {"error": ...} (not {"detail": ...}),
 * so callers must read `data.error` as well as `data.detail`.
 */
export const alumniApi = {
  landing: () => api.get<AlumniLandingPayload>('/alumni/landing'),
  directory: (params: DirectoryQuery = {}) =>
    api.get<AlumniProfile[]>('/alumni/directory', { params }),
  batches: () => api.get<AlumniBatch[]>('/alumni/batches'),
  standaloneDirectory: (params: StandaloneDirectoryQuery = {}) =>
    api.get<AlumniDirectoryResponse>('/alumni/', { params }),
  summary: (year: number) => api.get<AlumniBatchSummary>(`/alumni/batches/${year}/summary`),
  profile: (id: string) => api.get<AlumniProfileDetail>(`/alumni/${id}`),
  getMyProfile: () => api.get<AlumniProfile | null>('/alumni/me'),
  updateMyProfile: (body: Partial<AlumniClaimInput>) => api.patch<AlumniProfile>('/alumni/me', body),
  myEmployments: () => api.get<AlumniEmployment[]>('/alumni/me/employments'),
  replaceMyEmployments: (body: Omit<AlumniEmployment, 'id' | 'alumni_id' | 'created_at' | 'updated_at'>[]) =>
    api.put<AlumniEmployment[]>('/alumni/me/employments', body),
  importPreview: (file: File) => {
    const body = new FormData(); body.append('file', file);
    return api.post<AlumniImportPreview>('/alumni/admin/import/preview', body);
  },
  importCsv: (file: File) => {
    const body = new FormData(); body.append('file', file);
    return api.post<AlumniImportResult>('/alumni/admin/import', body);
  },
  claim: (body: AlumniClaimInput) => api.post<AlumniProfile>('/alumni/claim', body),
  dashboard: () => api.get<AlumniDashboardPayload>('/alumni/dashboard'),
  events: () => api.get<AlumniEvent[]>('/alumni/events'),
  rsvp: (eventId: string, rsvpStatus: EventRsvp['rsvp_status'] = 'attending') =>
    api.post<EventRsvp>(`/alumni/events/${eventId}/rsvp`, { rsvp_status: rsvpStatus }),
  scholarships: () => api.get<AlumniScholarship[]>('/alumni/scholarships'),
  applyScholarship: (scholarshipId: string, motivation: string) =>
    api.post<ScholarshipApplication>(`/alumni/scholarships/${scholarshipId}/apply`, { motivation }),
  mentors: () => api.get<AlumniProfile[]>('/alumni/mentors'),
  requestMentorship: (mentorId: string, note?: string) =>
    api.post<MentorshipPair>('/alumni/mentorship', {
      mentor_id: mentorId,
      mentee_note: note ?? null,
    }),
  news: () => api.get<AlumniNewsPost[]>('/alumni/news'),
  gallery: () => api.get<GalleryAlbum[]>('/alumni/gallery'),
  register: (body: AlumniRegisterInput) => api.post<RegisterResult>('/alumni/register', body),
  adminPending: () => api.get<AlumniProfile[]>('/alumni/admin/pending'),
  adminApprove: (profileId: string) =>
    api.patch<AlumniProfile>(`/alumni/admin/approve/${profileId}`),
  adminReject: (profileId: string, reason?: string) =>
    api.patch<AlumniProfile>(`/alumni/admin/reject/${profileId}`, reason ? { reason } : null),
};

export interface AlumniImportError { row: number; field?: string | null; message: string; }
export interface AlumniImportPreview { dry_run: boolean; total_rows: number; valid_rows: number; invalid_rows: number; errors: AlumniImportError[]; }
export interface AlumniImportResult extends AlumniImportPreview { imported_rows: number; updated_rows: number; }
