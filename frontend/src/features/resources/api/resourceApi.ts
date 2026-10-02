import { api } from '@/lib/axios';

export interface AcademicResource {
  id: string;
  title: string;
  description: string | null;
  category: string;
  course_code: string | null;
  file_name: string;
  file_size_bytes: number;
  mime_type: string;
  download_count: number;
  is_faculty_verified: boolean;
  uploader_name?: string | null;
  created_at: string;
}

export interface ResourceUploadInput {
  file: File;
  title: string;
  category: string;
  description?: string;
  course_code?: string;
}

export const resourceApi = {
  search: (q?: string, category?: string) =>
    api.get<AcademicResource[]>('/resources/search', { params: { q, category } }),
  upload: (input: ResourceUploadInput) => {
    const form = new FormData();
    form.append('file', input.file);
    form.append('title', input.title);
    form.append('category', input.category);
    if (input.description) form.append('description', input.description);
    if (input.course_code) form.append('course_code', input.course_code);
    return api.post<{ resource: AcademicResource; message: string }>('/resources', form);
  },
  download: (id: string) =>
    api.get<{ download_url: string; file_name: string; expires_in: number }>(
      `/resources/${id}/download`
    ),
  remove: (id: string) => api.delete(`/resources/${id}`),
};
