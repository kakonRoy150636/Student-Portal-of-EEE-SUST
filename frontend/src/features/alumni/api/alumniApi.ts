import { api } from '@/lib/axios';

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
}

export const alumniApi = {
  /** Returns null (HTTP 200) when the signed-in user has no claim yet. */
  getMyProfile: () => api.get<AlumniProfile | null>('/alumni/me'),
};
