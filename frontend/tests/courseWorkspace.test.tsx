import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { UserRole } from '@/types/auth';
import type { CourseAnnouncement, CourseWorkspace } from '@/types/courseWorkspace';

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  role: 'teacher',
}));

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 'teacher-1', role: mocks.role, full_name: 'Dr. Ada Rahman' },
    role: mocks.role,
    isAuthenticated: true,
    loading: false,
  }),
}));
vi.mock('@/lib/axios', () => ({ api: { get: mocks.get, post: mocks.post, patch: mocks.patch } }));

import CourseWorkspacePage from '../src/features/course-workspace/pages/CourseWorkspacePage';
import TeacherAssignmentPage from '../src/features/teacher-assignment/pages/TeacherAssignmentPage';

function response<T>(data: T) {
  return Promise.resolve({ data });
}

function announcement(overrides: Partial<CourseAnnouncement> = {}): CourseAnnouncement {
  return {
    id: 'announcement-1',
    offering_id: 'offering-1',
    author_id: 'teacher-1',
    author_name: 'Dr. Ada Rahman',
    title: 'Lecture update',
    body: 'Lecture moved to room 201. https://portal.test/room-201',
    announcement_type: 'class_update',
    status: 'published',
    audience: 'enrolled_students',
    is_pinned: false,
    publish_at: '2026-10-11T09:00:00Z',
    created_at: '2026-10-11T09:00:00Z',
    updated_at: '2026-10-11T09:00:00Z',
    archived_at: null,
    is_read: false,
    can_manage: false,
    can_publish: false,
    can_edit: false,
    can_archive: false,
    can_pin: false,
    ...overrides,
  };
}

function workspace(overrides: Partial<CourseWorkspace> = {}): CourseWorkspace {
  return {
    offering_id: 'offering-1',
    offering_status: 'published',
    course: {
      id: 'course-1', course_code: 'EEE 401', title: 'Power Systems II', credit_hours: 3, type: 'theory', description: 'Course description',
    },
    semester: {
      id: 1, title: 'Fall 2026', target_term: '4-1', is_active: true, start_date: '2026-07-01', end_date: '2026-12-31',
    },
    authorized_teachers: [{ teacher_id: 'teacher-1', teacher_name: 'Dr. Ada Rahman', role: 'provider' }],
    active_enrollment_count: 18,
    unread_announcement_count: 1,
    recent_activity: [],
    upcoming_schedules: [],
    resources: [],
    events: [],
    questions: [],
    permissions: { can_manage: true, can_publish: true, can_edit: true, can_archive: true, can_pin: true },
    can_manage: true,
    can_publish: true,
    can_edit: true,
    can_archive: true,
    can_pin: true,
    links: { self: '/course-offerings/offering-1/workspace', announcements: '/course-offerings/offering-1/announcements', resources: '/course-offerings/offering-1/resources', attendance: '/attendance/courses/offering-1/summary' },
    ...overrides,
  };
}

let currentWorkspace = workspace();
let currentFeed: CourseAnnouncement[] = [announcement({ is_pinned: true, is_read: false })];
type AnnouncementPostPayload = { title?: string; body?: string; status?: CourseAnnouncement['status'] };

function setupApi() {
  mocks.get.mockImplementation((path: string) => {
    if (path.endsWith('/workspace')) return response(currentWorkspace);
    if (path.endsWith('/announcements')) return response({ items: currentFeed, total: currentFeed.length, limit: 10, offset: 0, has_more: false });
    if (path.endsWith('/resources')) return response([]);
    if (path.endsWith('/available')) return response([]);
    if (path.endsWith('/assignment-requests/mine')) return response([]);
    if (path.endsWith('/semesters/active')) return response([]);
    throw new Error(`Unexpected GET ${path}`);
  });
  mocks.post.mockImplementation((path: string, payload?: AnnouncementPostPayload) => {
    if (path.endsWith('/announcements')) {
      const created = announcement({ id: 'announcement-created', title: payload?.title ?? 'Draft', body: payload?.body ?? 'Body', status: payload?.status ?? 'draft', can_manage: true, can_publish: true, can_edit: true, can_archive: true, can_pin: true, is_read: true });
      currentFeed = [created, ...currentFeed];
      return response(created);
    }
    if (path.endsWith('/publish')) return response(announcement({ status: 'published', can_manage: true, can_publish: false, can_edit: true, can_archive: true, can_pin: true, is_read: true }));
    if (path.endsWith('/archive')) return response(announcement({ status: 'archived', can_manage: true, can_publish: false, can_edit: false, can_archive: false, can_pin: false, is_read: true }));
    throw new Error(`Unexpected POST ${path}`);
  });
  mocks.patch.mockImplementation((path: string) => {
    if (path.startsWith('/course-announcements/')) return response({ announcement_id: 'announcement-1', read_at: '2026-10-12T09:00:00Z', is_read: true });
    if (path.endsWith('/pin')) return response(announcement({ is_pinned: true, can_manage: true, can_publish: false, can_edit: true, can_archive: true, can_pin: true, is_read: true }));
    return response(announcement({ can_manage: true, can_publish: true, can_edit: true, can_archive: true, can_pin: true, is_read: true }));
  });
}

function renderWorkspace(path = '/teacher/courses/offering-1') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[path]}><Routes><Route path="/teacher/courses/:offeringId" element={<CourseWorkspacePage />} /><Route path="/student/courses/:offeringId" element={<CourseWorkspacePage />} /><Route path="/course-offerings/:offeringId/workspace" element={<CourseWorkspacePage />} /></Routes></MemoryRouter></QueryClientProvider>);
  return client;
}

beforeEach(() => {
  mocks.role = UserRole.TEACHER;
  currentWorkspace = workspace();
  currentFeed = [announcement({ is_pinned: true, is_read: false })];
  mocks.get.mockReset();
  mocks.post.mockReset();
  mocks.patch.mockReset();
  setupApi();
});

afterEach(() => cleanup());

describe('CourseWorkspacePage', () => {
  it('renders a protected workspace route, summary, and horizontally scrollable tabs', async () => {
    renderWorkspace();
    expect(await screen.findByRole('heading', { name: 'Power Systems II' })).toBeTruthy();
    expect(screen.getAllByText('18').length).toBeGreaterThan(0);
    const tablist = screen.getByRole('tablist', { name: 'Course workspace tabs' });
    expect(tablist.className).toContain('overflow-x-auto');
    expect(within(tablist).getAllByRole('tab')).toHaveLength(10);
    expect(mocks.get).toHaveBeenCalledWith('/course-offerings/offering-1/workspace', expect.objectContaining({ signal: expect.anything() }));
  });

  it('shows teacher course-card workspace entry with offering details', async () => {
    mocks.get.mockImplementation((path: string) => {
      if (path.endsWith('/semesters/active')) return response([{ id: 1, title: 'Fall 2026', target_term: '4-1', is_active: true, start_date: '2026-07-01', end_date: '2026-12-31' }]);
      if (path.endsWith('/available')) return response([{ id: 'offering-1', course_id: 'course-1', semester_id: 1, semester_title: 'Fall 2026', semester_is_active: true, course_code: 'EEE 401', course_title: 'Power Systems II', course_type: 'theory', credit_hours: 3, publication_status: 'published', assigned_teachers: [{ teacher_id: 'teacher-1', teacher_name: 'Dr. Ada Rahman', role: 'provider' }], created_by: 'teacher-1', published_by: 'teacher-1', published_at: '2026-10-01T00:00:00Z', request_status: null }]);
      if (path.endsWith('/assignment-requests/mine')) return response([]);
      if (path.endsWith('/workspace')) return response(currentWorkspace);
      throw new Error(`Unexpected GET ${path}`);
    });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
    render(<QueryClientProvider client={client}><TeacherAssignmentPage /></QueryClientProvider>);
    expect(await screen.findByRole('heading', { name: 'Your eligible courses' })).toBeTruthy();
    const entry = screen.getByRole('link', { name: /Open workspace/i });
    expect(entry.getAttribute('href')).toBe('/teacher/courses/offering-1');
    expect(screen.getByText('18')).toBeTruthy();
  });

  it('creates a plain-text draft and schedules an announcement from the dialog', async () => {
    const user = userEvent.setup();
    renderWorkspace('/teacher/courses/offering-1?tab=announcements');
    await user.click(await screen.findByRole('button', { name: 'Create announcement' }));
    const dialog = within(screen.getByRole('dialog', { name: 'Create announcement' }));
    await user.type(dialog.getByLabelText('Title'), 'Draft notice');
    await user.type(dialog.getByLabelText('Body'), '<script>not html</script>Plain text');
    await user.click(dialog.getByRole('button', { name: 'Save draft' }));
    await waitFor(() => expect(mocks.post).toHaveBeenCalledWith('/course-offerings/offering-1/announcements', expect.objectContaining({ title: 'Draft notice', body: '<script>not html</script>Plain text', status: 'draft', publish_at: null })));

    await user.click(screen.getByRole('button', { name: 'Close dialog' }));
    await user.click(screen.getByRole('button', { name: 'Create announcement' }));
    const scheduled = within(screen.getByRole('dialog', { name: 'Create announcement' }));
    await user.type(scheduled.getByLabelText('Title'), 'Scheduled notice');
    await user.type(scheduled.getByLabelText('Body'), 'Later');
    await user.selectOptions(scheduled.getByLabelText('Status'), 'scheduled');
    const future = new Date(Date.now() + 86_400_000);
    const pad = (value: number) => String(value).padStart(2, '0');
    const localDate = `${future.getFullYear()}-${pad(future.getMonth() + 1)}-${pad(future.getDate())}T${pad(future.getHours())}:${pad(future.getMinutes())}`;
    await user.type(scheduled.getByLabelText('Publish at'), localDate);
    await user.click(scheduled.getByRole('button', { name: 'Schedule announcement' }));
    await waitFor(() => expect(mocks.post).toHaveBeenLastCalledWith('/course-offerings/offering-1/announcements', expect.objectContaining({ title: 'Scheduled notice', status: 'scheduled', publish_at: expect.any(String) })));
  });

  it('keeps the announcement dialog open after a save error and allows retry with the same entries', async () => {
    const user = userEvent.setup();
    mocks.post.mockRejectedValueOnce(new Error('Announcement service unavailable'));
    renderWorkspace('/teacher/courses/offering-1?tab=announcements');
    await user.click(await screen.findByRole('button', { name: 'Create announcement' }));
    const dialog = within(screen.getByRole('dialog', { name: 'Create announcement' }));
    await user.type(dialog.getByLabelText('Title'), 'Retry notice');
    await user.type(dialog.getByLabelText('Body'), 'Keep this body');
    await user.click(dialog.getByRole('button', { name: 'Save draft' }));
    expect((await dialog.findByRole('alert')).textContent).toContain('Announcement service unavailable');
    expect(dialog.getByLabelText('Title')).toHaveProperty('value', 'Retry notice');
    await user.click(dialog.getByRole('button', { name: 'Save draft' }));
    await waitFor(() => expect(mocks.post).toHaveBeenCalledTimes(2));
    expect(await screen.findByRole('dialog', { name: 'Retry notice' })).toBeTruthy();
  });

  it('publishes now and hides lifecycle controls for unauthorized student feeds while marking unread open', async () => {
    const user = userEvent.setup();
    currentFeed = [announcement({ can_manage: true, can_publish: true, can_edit: true, can_archive: true, can_pin: true, status: 'draft', is_read: true }), announcement({ id: 'announcement-student', title: 'Pinned student notice', is_pinned: true, is_read: false })];
    renderWorkspace('/teacher/courses/offering-1?tab=announcements');
    await user.click(await screen.findByRole('button', { name: 'Publish now' }));
    await waitFor(() => expect(mocks.post).toHaveBeenCalledWith('/course-offerings/offering-1/announcements/announcement-1/publish'));

    cleanup();
    mocks.role = UserRole.STUDENT;
    setupApi();
    currentFeed = [announcement({ id: 'announcement-student', title: 'Pinned student notice', is_pinned: true, is_read: false })];
    renderWorkspace('/student/courses/offering-1?tab=announcements');
    expect(await screen.findByText('Pinned')).toBeTruthy();
    expect(screen.getAllByText('Unread').length).toBeGreaterThan(0);
    expect(screen.queryByRole('button', { name: 'Create announcement' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Publish now' })).toBeNull();
    expect(screen.queryByRole('button', { name: /Archive/ })).toBeNull();
    await user.click(screen.getByRole('button', { name: 'Open announcement Pinned student notice' }));
    await waitFor(() => expect(mocks.patch).toHaveBeenCalledWith('/course-announcements/announcement-student/read'));
  });

  it('renders loading, empty, and retryable error states', async () => {
    let workspaceCalls = 0;
    mocks.get.mockImplementation((path: string) => {
      if (path.endsWith('/workspace')) {
        workspaceCalls += 1;
        if (workspaceCalls === 1) return new Promise(() => {});
        return response(currentWorkspace);
      }
      if (path.endsWith('/announcements')) return response({ items: [], total: 0, limit: 10, offset: 0, has_more: false });
      return response([]);
    });
    renderWorkspace('/teacher/courses/offering-1');
    expect(document.querySelector('[aria-busy="true"]')).toBeTruthy();
    cleanup();

    let feedCalls = 0;
    mocks.get.mockImplementation((path: string) => {
      if (path.endsWith('/workspace')) return response(currentWorkspace);
      if (path.endsWith('/announcements')) {
        feedCalls += 1;
        if (feedCalls === 1) return Promise.reject(new Error('Announcement service unavailable'));
        return response({ items: [], total: 0, limit: 10, offset: 0, has_more: false });
      }
      return response([]);
    });
    renderWorkspace('/teacher/courses/offering-1?tab=announcements');
    expect(await screen.findByText('Could not load announcements.')).toBeTruthy();
    await userEvent.setup().click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByText('No announcements found')).toBeTruthy();
  });
});
