import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { flattenNav } from '@/layouts/nav';
import { UserRole } from '@/types/auth';
import type { CourseCatalogueItem, CourseOffering, Semester, TeacherAssignmentRequest } from '@/types/academic';
import { ProtectedRoute } from '@/routes/ProtectedRoute';

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  authRole: 'super_admin',
}));

vi.mock('@/lib/axios', () => ({ api: { get: mocks.get, post: mocks.post, patch: mocks.patch } }));
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ loading: false, isAuthenticated: true, role: mocks.authRole }),
}));

import AdminAcademicPage from '../src/features/admin/pages/AdminAcademicPage';

const course: CourseCatalogueItem = {
  id: 'course-1',
  course_code: 'EEE 401',
  title: 'Advanced Power Systems',
  credits: 3,
  type: 'theory',
  description: null,
};

const semester: Semester = {
  id: 1,
  title: 'Fall 2026',
  is_active: true,
  start_date: '2026-07-01',
  end_date: '2026-12-31',
};

const offering: CourseOffering = {
  id: 'offering-1',
  course_id: course.id,
  semester_id: semester.id,
  semester_title: semester.title,
  semester_is_active: true,
  course_code: course.course_code,
  course_title: course.title,
  course_type: course.type,
  credit_hours: course.credits,
  publication_status: 'draft',
  assigned_teachers: [],
  created_by: 'admin-1',
  published_by: null,
  published_at: null,
  request_status: null,
};

const request: TeacherAssignmentRequest = {
  id: 'request-1',
  course_offering_id: offering.id,
  teacher_id: 'teacher-1',
  teacher_name: 'Dr. Ada Rahman',
  course_code: offering.course_code,
  course_title: offering.course_title,
  semester_id: semester.id,
  semester_title: semester.title,
  status: 'pending',
  decided_by: null,
  decided_at: null,
  rejection_reason: null,
  created_at: '2026-07-01T00:00:00Z',
  updated_at: '2026-07-01T00:00:00Z',
};

function response<T>(data: T) {
  return Promise.resolve({ data });
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <MemoryRouter>
      <QueryClientProvider client={client}><AdminAcademicPage /></QueryClientProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  mocks.authRole = UserRole.SUPER_ADMIN;
  mocks.get.mockImplementation((path: string) => {
    if (path === '/course-offerings') return response([offering]);
    if (path === '/courses') return response([course]);
    if (path.endsWith('/semesters/active')) return response([semester]);
    if (path.endsWith('/assignment-requests')) return response([request]);
    throw new Error(`Unexpected GET ${path}`);
  });
  mocks.post.mockResolvedValue(response(offering));
  mocks.patch.mockResolvedValue(response(request));
});

afterEach(() => cleanup());

describe('admin academic management', () => {
  it('shows academic management only to super administrators in navigation', () => {
    expect(flattenNav(UserRole.SUPER_ADMIN).some((item) => item.name === 'Academic Management')).toBe(true);
    expect(flattenNav(UserRole.TEACHER).some((item) => item.name === 'Academic Management')).toBe(false);
    expect(flattenNav(UserRole.STUDENT).some((item) => item.name === 'Academic Management')).toBe(false);
  });

  it('redirects non-admin users away from the academic route', () => {
    mocks.authRole = UserRole.TEACHER;
    render(
      <MemoryRouter initialEntries={['/admin/academic']}>
        <Routes>
          <Route path="/admin/academic" element={<ProtectedRoute roles={[UserRole.SUPER_ADMIN]}><p>Academic page</p></ProtectedRoute>} />
          <Route path="/dashboard" element={<p>Dashboard</p>} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.queryByText('Academic page')).toBeNull();
    expect(screen.getByText('Dashboard')).toBeTruthy();
  });

  it('approves a pending teacher request after confirmation', async () => {
    const user = userEvent.setup();
    renderPage();

    expect(await screen.findByText('Academic management')).toBeTruthy();
    expect((await screen.findAllByText('draft')).length).toBeGreaterThan(0);
    const approveButtons = await screen.findAllByRole('button', { name: /Approve Dr\. Ada Rahman for EEE 401/i });
    await user.click(approveButtons[0]);
    expect(await screen.findByRole('heading', { name: 'Approve teacher assignment?' })).toBeTruthy();
    await user.click(screen.getByRole('button', { name: 'Approve request' }));

    await waitFor(() => expect(mocks.patch).toHaveBeenCalledWith(
      '/course-offerings/assignment-requests/request-1',
      { decision: 'approve' },
    ));
  });

  it('rejects a pending request with an optional reason', async () => {
    const user = userEvent.setup();
    renderPage();

    const rejectButtons = await screen.findAllByRole('button', { name: /Reject Dr\. Ada Rahman for EEE 401/i });
    await user.click(rejectButtons[0]);
    await user.type(screen.getByLabelText('Rejection reason (optional)'), 'Another teacher was selected.');
    await user.click(screen.getByRole('button', { name: 'Reject request' }));

    await waitFor(() => expect(mocks.patch).toHaveBeenCalledWith(
      '/course-offerings/assignment-requests/request-1',
      { decision: 'reject', rejection_reason: 'Another teacher was selected.' },
    ));
  });
});
