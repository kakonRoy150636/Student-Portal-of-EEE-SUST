import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { CourseEnrollment, CourseOffering, Semester } from '@/types/academic';

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  user: { id: 'student-1', role: 'student' },
}));

vi.mock('@/contexts/AuthContext', () => ({ useAuth: () => ({ user: mocks.user }) }));
vi.mock('@/lib/axios', () => ({ api: { get: mocks.get, post: mocks.post } }));

import CourseSelectionPage from '../src/features/course-selection/pages/CourseSelectionPage';

const semester: Semester = {
  id: 1,
  title: 'Fall 2026',
  is_active: true,
  start_date: '2026-07-01',
  end_date: '2026-12-31',
};

const offering: CourseOffering = {
  id: 'offering-1',
  course_id: 'course-1',
  semester_id: 1,
  semester_title: semester.title,
  semester_is_active: true,
  course_code: 'EEE 201',
  course_title: 'Signals and Systems',
  course_type: 'theory',
  credit_hours: 3,
  publication_status: 'published',
  assigned_teachers: [{ teacher_id: 'teacher-1', teacher_name: 'Dr. Ada Rahman', role: 'course_teacher' }],
  created_by: null,
  published_by: 'admin-1',
  published_at: '2026-07-01T00:00:00Z',
  request_status: null,
};

let offerings: CourseOffering[];
let enrollments: CourseEnrollment[];
let activeCreditTotal: number;

function response<T>(data: T) {
  return Promise.resolve({ data });
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const invalidate = vi.spyOn(client, 'invalidateQueries');
  const rendered = render(<QueryClientProvider client={client}><CourseSelectionPage /></QueryClientProvider>);
  return { client, invalidate, ...rendered };
}

function setupApi() {
  mocks.get.mockImplementation((path: string) => {
    if (path.endsWith('/semesters/active')) return response([semester]);
    if (path.endsWith('/published')) return response(offerings);
    if (path.endsWith('/enrollments/me')) return response(enrollments);
    if (path.endsWith('/enrollments/me/credits')) return response({ active_credit_total: activeCreditTotal });
    throw new Error(`Unexpected GET ${path}`);
  });
  mocks.post.mockImplementation(async (path: string) => {
    if (path.endsWith('/enroll')) {
      const next: CourseEnrollment = {
        id: 7,
        course_offering_id: offering.id,
        student_id: mocks.user.id,
        status: 'enrolled',
        course_code: offering.course_code,
        course_title: offering.course_title,
        semester_id: offering.semester_id,
        semester_title: offering.semester_title,
        credit_hours: offering.credit_hours,
        enrolled_at: '2026-07-01T00:00:00Z',
        updated_at: '2026-07-01T00:00:00Z',
        dropped_at: null,
      };
      enrollments = [next];
      activeCreditTotal = 3;
      return response(next);
    }
    if (path.endsWith('/drop')) {
      enrollments = [{ ...enrollments[0], status: 'drop', dropped_at: '2026-07-02T00:00:00Z' }];
      activeCreditTotal = 0;
      return response(enrollments[0]);
    }
    if (path.endsWith('/reselect')) {
      enrollments = [{ ...enrollments[0], status: 'enrolled', dropped_at: null }];
      activeCreditTotal = 3;
      return response(enrollments[0]);
    }
    throw new Error(`Unexpected POST ${path}`);
  });
}

beforeEach(() => {
  offerings = [offering];
  enrollments = [];
  activeCreditTotal = 0;
  mocks.get.mockReset();
  mocks.post.mockReset();
  setupApi();
});

afterEach(() => cleanup());

describe('CourseSelectionPage', () => {
  it('renders server data and selects a course, invalidating dependent academic queries', async () => {
    const { invalidate } = renderPage();

    expect(await screen.findByText('EEE 201')).toBeTruthy();
    expect(screen.getAllByText('Fall 2026').length).toBeGreaterThan(0);
    expect(screen.getByText('Dr. Ada Rahman')).toBeTruthy();
    expect(screen.getByLabelText('Total active credits: 0')).toBeTruthy();

    await userEvent.setup().click(screen.getByRole('button', { name: 'Select EEE 201' }));
    await waitFor(() => expect(screen.getByText('Enrolled')).toBeTruthy());
    expect(mocks.post).toHaveBeenCalledWith('/course-offerings/offering-1/enroll', { enrollment_type: 'enrolled' });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['dashboard'] });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['schedules'] });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['attendance'] });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['notifications'] });
  });

  it('confirms a drop and offers reselection for the dropped course', async () => {
    enrollments = [{
      id: 7, course_offering_id: offering.id, student_id: mocks.user.id, status: 'enrolled',
      course_code: offering.course_code, course_title: offering.course_title, semester_id: 1,
      semester_title: semester.title, credit_hours: 3, enrolled_at: '2026-07-01T00:00:00Z',
      updated_at: '2026-07-01T00:00:00Z', dropped_at: null,
    }];
    activeCreditTotal = 3;
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole('button', { name: 'Drop EEE 201' }));
    expect(screen.getByRole('heading', { name: 'Drop EEE 201?' })).toBeTruthy();
    await user.click(screen.getByRole('button', { name: 'Confirm drop' }));
    await waitFor(() => expect(screen.getByText('Dropped')).toBeTruthy());
    expect(screen.getByRole('button', { name: 'Reselect EEE 201' })).toBeTruthy();
  });

  it('reselects a dropped course through the same enrollment record', async () => {
    enrollments = [{
      id: 7, course_offering_id: offering.id, student_id: mocks.user.id, status: 'drop',
      course_code: offering.course_code, course_title: offering.course_title, semester_id: 1,
      semester_title: semester.title, credit_hours: 3, enrolled_at: '2026-07-01T00:00:00Z',
      updated_at: '2026-07-02T00:00:00Z', dropped_at: '2026-07-02T00:00:00Z',
    }];
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole('button', { name: 'Reselect EEE 201' }));
    await waitFor(() => expect(screen.getByText('Enrolled')).toBeTruthy());
    expect(mocks.post).toHaveBeenCalledWith('/course-offerings/enrollments/7/reselect', { enrollment_type: 'enrolled' });
  });

  it('disables actions for unpublished and inactive offerings', async () => {
    offerings = [
      offering,
      { ...offering, id: 'draft-1', course_code: 'EEE 202', publication_status: 'draft' },
      { ...offering, id: 'inactive-1', course_code: 'EEE 203', semester_id: 2, semester_is_active: false },
    ];
    renderPage();

    expect((await screen.findByRole('button', { name: 'Select EEE 202' }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole('button', { name: 'Select EEE 203' }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getAllByText(/only published offerings in an active semester/i).length).toBe(2);
  });

  it('shows empty and loading states from the backend contract', async () => {
    offerings = [];
    const { unmount } = renderPage();
    expect(await screen.findByText('No courses published')).toBeTruthy();
    unmount();

    mocks.get.mockImplementation(() => new Promise(() => {}));
    renderPage();
    expect(document.querySelector('[aria-busy="true"]')).toBeTruthy();
  });

  it('shows API errors and a mutation conflict state', async () => {
    mocks.get.mockRejectedValueOnce(new Error('API offline'));
    renderPage();
    expect(await screen.findByText('Could not load course selection.')).toBeTruthy();

    cleanup();
    setupApi();
    mocks.post.mockRejectedValue({
      isAxiosError: true,
      response: { status: 409, data: { detail: 'This course was selected elsewhere.' } },
    });
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Select EEE 201' }));
    expect(await screen.findByText('Course selection conflict')).toBeTruthy();
    expect(screen.getByText('This course was selected elsewhere.')).toBeTruthy();
  });
});
